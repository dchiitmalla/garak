#!/usr/bin/env python
# SPDX-FileCopyrightText: Portions Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

# highlight failing probes
# give ten +ve and ten -ve examples from failing probes
# takes report.jsonl, optional bag.json as input

from collections import defaultdict
import json
import random
import sys

import garak.analyze
import garak.analyze.calibration
from garak.probes.base import Tier

PROBE_DETECTOR_SEP = "+"


def build_tiers() -> dict:
    from garak._plugins import enumerate_plugins, plugin_info

    tiers = {}
    for tier in Tier:
        tiers[tier] = []

    for plugin, _ in enumerate_plugins("probes"):
        details = plugin_info(plugin)
        _, plugin_name = plugin.split(".", 1)
        tiers[Tier(details["tier"])].append(plugin_name)

    return tiers


tiers = build_tiers()
# load in the scores

c = garak.analyze.calibration.Calibration()
probe_detector_scores = {}
pos_examples = defaultdict(list)
neg_examples = defaultdict(list)

print(sys.argv[1])
print()

with open(sys.argv[1], "r", encoding="utf-8") as report_file:
    g = (json.loads(line.strip()) for line in open(sys.argv[1]) if line.strip())
    for record in g:
        if record["entry_type"] == "eval":
            passrate = record["passed"] / record["total"] if record["total"] > 0 else 0
            probe_module, probe_classname = record["probe"].split(".", 1)
            detector = record["detector"].replace("detector.", "")
            detector_module, detector_classname = detector.split(".", 1)
            z = c.get_z_score(
                probe_module,
                probe_classname,
                detector_module,
                detector_classname,
                passrate,
            )
            probe_detector_scores[
                f"{record['probe']}{PROBE_DETECTOR_SEP}{detector}"
            ] = {
                "passrate": passrate,
                "z": z,
            }
        elif record["entry_type"] == "attempt" and record["status"] == 2:
            results = record["detector_results"]
            for detector_name in results:
                for i, score in enumerate(results[detector_name]):
                    try:
                        fields = [record["prompt"], record["outputs"][i]]
                        if "triggers" in record["notes"].keys():
                            fields.append(record["notes"]["triggers"])
                        if score > 0.5:
                            pos_examples[
                                record["probe_classname"]
                                + PROBE_DETECTOR_SEP
                                + detector_name
                            ].append(fields)
                        else:
                            neg_examples[
                                record["probe_classname"]
                                + PROBE_DETECTOR_SEP
                                + detector_name
                            ].append(fields)
                    except IndexError:
                        continue


def _print_examples(probe_detector):
    print("\nexamples - failures")
    excerpt = pos_examples[probe_detector]
    random.shuffle(excerpt)
    for entry in excerpt[0:10]:
        print("prompt:\t" + repr(entry[0]))
        if len(entry) == 3:
            print("trigger:\t" + repr(entry[2]))
        print("response:\t" + repr(entry[1]))
    print("\nexamples - OK")
    excerpt = neg_examples[probe_detector]
    random.shuffle(excerpt)
    for entry in excerpt[0:10]:
        print("prompt:\t" + repr(entry[0]))
        if len(entry) == 3:
            print("trigger:\t" + repr(entry[2]))
        print("response:\t" + repr(entry[1]))


print("Tier 1")
t1_probe_names = tiers[Tier.TIER_1]
for probe_detector in probe_detector_scores.keys():
    if probe_detector.split(PROBE_DETECTOR_SEP)[0] in t1_probe_names:
        z, passrate = (
            probe_detector_scores[probe_detector]["z"],
            probe_detector_scores[probe_detector]["passrate"],
        )
        if passrate < garak.analyze.SCORE_DEFCON_BOUNDS.BELOW_AVG or (
            z is not None and z < garak.analyze.ZSCORE_DEFCON_BOUNDS.BELOW_AVG
        ):
            print("\n" + probe_detector)
            if passrate < garak.analyze.SCORE_DEFCON_BOUNDS.BELOW_AVG:
                print(f"low pass rate {passrate:0.4f}")
            if z is not None and z < garak.analyze.ZSCORE_DEFCON_BOUNDS.BELOW_AVG:
                print(f"low z         {z:-0.4f}")
            _print_examples(probe_detector)
        else:
            print(
                f"\n{probe_detector} within bounds (passrate: {passrate:0.4f} z: {z})\n"
            )

print("\nTier 2")
t2_probe_names = tiers[Tier.TIER_2]
for probe_detector in probe_detector_scores.keys():
    if probe_detector.split(PROBE_DETECTOR_SEP)[0] in t2_probe_names:
        z, passrate = (
            probe_detector_scores[probe_detector]["z"],
            probe_detector_scores[probe_detector]["passrate"],
        )
        if z is not None and z < garak.analyze.ZSCORE_DEFCON_BOUNDS.BELOW_AVG:
            print("\n" + probe_detector)
            print(f"low z   {z:-0.4f}")
            _print_examples(probe_detector)
        else:
            print(
                f"\n{probe_detector} within bounds (passrate: {passrate:0.4f} z: {z})\n"
            )

print("\nNot processed:")
t1_t2_probes = t1_probe_names + t2_probe_names
for entry in [
    probe_detector
    for probe_detector in probe_detector_scores.keys()
    if probe_detector.split(PROBE_DETECTOR_SEP)[0] not in t1_t2_probes
]:
    print(entry)
