#!/usr/bin/env python

"""Generate reports from garak report JSONL"""

from collections import defaultdict
import html
import importlib
import json
import markdown
import os
import pprint
import re
import statistics
import sys
import typing

import jinja2
import sqlite3

import garak
from garak import _config
from garak.data import path as data_path
import garak.analyze
import garak.analyze.calibration


if not _config.loaded:
    _config.load_config()

templateLoader = jinja2.FileSystemLoader(
    searchpath=_config.transient.package_dir / "analyze" / "templates"
)
templateEnv = jinja2.Environment(loader=templateLoader)

header_template = templateEnv.get_template("digest_header.jinja")
footer_template = templateEnv.get_template("digest_footer.jinja")
group_template = templateEnv.get_template("digest_group.jinja")
probe_template = templateEnv.get_template("digest_probe.jinja")
detector_template = templateEnv.get_template("digest_detector.jinja")
end_module = templateEnv.get_template("digest_end_module.jinja")
about_z_template = templateEnv.get_template("digest_about_z.jinja")


misp_resource_file = data_path / "misp_descriptions.tsv"
misp_descriptions = {}
if os.path.isfile(misp_resource_file):
    with open(misp_resource_file, "r", encoding="utf-8") as f:
        for line in f:
            key, title, descr = line.strip().split("\t")
            misp_descriptions[key] = (title, descr)


def map_score(score: float) -> int:
    """assign a defcon class (i.e. 1-5, 1=worst) to a %age score 0.0-100.0"""
    if score < garak.analyze.ABSOLUTE_DEFCON_BOUNDS.TERRIBLE * 100.0:
        return 1
    if score < garak.analyze.ABSOLUTE_DEFCON_BOUNDS.BELOW_AVG * 100.0:
        return 2
    if score < garak.analyze.ABSOLUTE_DEFCON_BOUNDS.ABOVE_AVG * 100.0:
        return 3
    if score < garak.analyze.ABSOLUTE_DEFCON_BOUNDS.EXCELLENT * 100.0:
        return 4
    return 5


def plugin_docstring_to_description(docstring):
    return docstring.split("\n")[0]


def _extract_report_object(filename: typing.IO) -> dict:
    return {}

def compile_digest(
    report_path,
    taxonomy=_config.reporting.taxonomy,
    group_aggregation_function=_config.reporting.group_aggregation_function,
):
    evals = []
    payloads = []
    setup = defaultdict(str)

    """
    digest_object structure

    meta: garak_version, calibration_info, config_info, run_name, ..
    probe_group: name, description
        probe: name, tags, description
            detector: name, description, attempt_count, passes_count, skip_count, relative_score, relative_defcon, absolute_score, relative_defcon
    """
    report_digest = {
        "meta": {},
        "probe_group": {},
    }

    with open(report_path, "r", encoding="utf-8") as reportfile:
        for line in reportfile:
            record = json.loads(line.strip())
            if record["entry_type"] == "eval":
                evals.append(record)
            elif record["entry_type"] == "init":
                garak_version = record["garak_version"]
                start_time = record["start_time"]
                run_uuid = record["run"]
            elif record["entry_type"] == "start_run setup":
                setup = record
            elif record["entry_type"] == "payload_init":
                payloads.append(
                    record["payload_name"]
                    + "  "
                    + pprint.pformat(record, sort_dicts=True, width=60)
                )

    calibration = garak.analyze.calibration.Calibration()
    calibration_used = False

    report_digest["meta"]["calibration"] = calibration.metadata

    header_content = {
            "reportfile": report_path.split(os.sep)[-1],
            "garak_version": garak_version,
            "start_time": start_time,
            "run_uuid": run_uuid,
            "setup": setup,
            "probespec": setup["plugins.probe_spec"],
            "model_type": setup["plugins.model_type"],
            "model_name": setup["plugins.model_name"],
            "payloads": payloads,
            "group_aggregation_function": _config.reporting.group_aggregation_function,
        }

    report_digest["meta"] = header_content
    header_content["setup"] = pprint.pformat(header_content["setup"], sort_dicts=True, width=60),
    digest_content = header_template.render(header_content)


    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    # build a structured obj: probemodule.probeclass.detectorname = %

    create_table = """create table results(
        probe_module VARCHAR(255) not null,
        probe_group VARCHAR(255) not null,
        probe_class VARCHAR(255) not null,
        detector VARCHAR(255) not null, 
        score FLOAT not null,
        instances INT not null
    );"""

    cursor.execute(create_table)

    for eval in evals:
        eval["probe"] = eval["probe"].replace("probes.", "")
        pm, pc = eval["probe"].split(".")
        detector = eval["detector"].replace("detector.", "")
        score = eval["passed"] / eval["total"] if eval["total"] else 0
        instances = eval["total"]
        groups = []
        if taxonomy is not None:
            # get the probe tags
            m = importlib.import_module(f"garak.probes.{pm}")
            tags = getattr(m, pc).tags
            for tag in tags:
                if tag.split(":")[0] == taxonomy:
                    groups.append(":".join(tag.split(":")[1:]))
            if groups == []:
                groups = ["other"]
        else:
            groups = [pm]
        # add a row for each group
        for group in groups:
            cursor.execute(
                f"insert into results values ('{pm}', '{group}', '{pc}', '{detector}', '{score}', '{instances}')"
            )

    # calculate per-probe scores

    res = cursor.execute(
        "select distinct probe_group from results order by probe_group"
    )
    group_names = [i[0] for i in res.fetchall()]

    # top score: % of passed probes
    # probe score: mean of detector scores

    # let's build a dict of per-probe score

    for probe_group in group_names:

        report_digest["probe_group"][probe_group] = {}

        group_score = None  # range 0.0--100.0
        res = cursor.execute(
            f"select score*100 as s from results where probe_group = '{probe_group}';"
        )
        probe_scores = [i[0] for i in res.fetchall()]

        # main aggregation function here
        match group_aggregation_function:
            # get all the scores

            case "mean":
                group_score = statistics.mean(probe_scores)
            case "minimum":
                group_score = min(probe_scores)
            case "median":
                group_score = statistics.median(probe_scores)
            case "lower_quartile":
                if len(probe_scores) == 1:
                    group_score = probe_scores[0]
                else:
                    group_score = statistics.quantiles(probe_scores, method="inclusive")[0]
            case "mean_minus_sd":
                if len(probe_scores) == 1:
                    group_score = probe_scores[0]
                else:
                    group_score = statistics.mean(probe_scores) - statistics.stdev(
                        probe_scores
                    )
            case "proportion_passing":
                group_score = 100.0 * (
                    len([p for p in probe_scores if p > garak.analyze.ABSOLUTE_DEFCON_BOUNDS.BELOW_AVG * 100]) / len(probe_scores)
                )
            case _:
                group_score = min(probe_scores)  # minimum as default
                group_aggregation_function += " (unrecognised, used 'minimum')"

        group_doc = f"Probes tagged {probe_group}"
        group_link = ""

        probe_group_name = probe_group
        if taxonomy is None:
            probe_module = re.sub("[^0-9A-Za-z_]", "", probe_group)
            m = importlib.import_module(f"garak.probes.{probe_module}")
            group_doc = markdown.markdown(plugin_docstring_to_description(m.__doc__))
            group_link = (
                f"https://reference.garak.ai/en/latest/garak.probes.{probe_group}.html"
            )
        elif probe_group != "other":
            probe_group_name = f"{taxonomy}:{probe_group}"
            if probe_group_name in misp_descriptions:
                probe_group_name, group_doc = misp_descriptions[probe_group_name]
        else:
            probe_group_name = "Uncategorized"

        digest_content += group_template.render(
            {
                "group": probe_group_name,
                "show_top_group_score": _config.reporting.show_top_group_score,
                "group_score": f"{group_score:.1f}%",
                "severity": map_score(group_score),
                "doc": group_doc,
                "group_link": group_link,
                "group_aggregation_function": group_aggregation_function,
            }
        )

        report_digest["probe_group"][probe_group]["name"] = probe_group_name
        report_digest["probe_group"][probe_group]["group_score"] = group_score
        report_digest["probe_group"][probe_group]["group_severity"] = map_score(group_score)
        report_digest["probe_group"][probe_group]["group_doc"] = group_doc
        report_digest["probe_group"][probe_group]["group_link"] = group_link
        report_digest["probe_group"][probe_group]["aggregation_function"] = group_aggregation_function
        report_digest["probe_group"][probe_group]["probes"] = {}


        if group_score < 100.0 or _config.reporting.show_100_pass_modules:
            res = cursor.execute(
                f"select probe_module, probe_class, min(score)*100 as s from results where probe_group='{probe_group}' group by probe_class order by s asc, probe_class asc;"
            )
            for probe_module, probe_class, absolute_score in res.fetchall():
                pm = importlib.import_module(f"garak.probes.{probe_module}")
                probe_description = plugin_docstring_to_description(
                    getattr(pm, probe_class).__doc__
                )
                probe_plugin_name = f"{probe_module}.{probe_class}"
                digest_content += probe_template.render(
                    {
                        "plugin_name": probe_plugin_name,
                        "plugin_score": f"{absolute_score:.1f}%",
                        "severity": map_score(absolute_score),
                        "plugin_descr": html.escape(probe_description),
                    }
                )

                report_digest["probe_group"][probe_group]["probes"][probe_plugin_name] = {}
                report_digest["probe_group"][probe_group]["probes"][probe_plugin_name]["name"] = probe_plugin_name
                report_digest["probe_group"][probe_group]["probes"][probe_plugin_name]["descr"] = probe_description
                report_digest["probe_group"][probe_group]["probes"][probe_plugin_name]["detectors"] = {}
                

                res = cursor.execute(
                    f"select detector, score*100 from results where probe_group='{probe_group}' and probe_class='{probe_class}' order by score asc, detector asc;"
                )
                for detector, score in res.fetchall():
                    detector = re.sub(r"[^0-9A-Za-z_.]", "", detector)
                    report_digest["probe_group"][probe_group]["probes"][probe_plugin_name]["detectors"][detector] = {}
                    detector_module, detector_class = detector.split(".")
                    dm = importlib.import_module(
                        f"garak.detectors.{detector_module}"
                    )
                    detector_description = plugin_docstring_to_description(
                        getattr(dm, detector_class).__doc__
                    )

                    zscore = calibration.get_z_score(
                        probe_module,
                        probe_class,
                        detector_module,
                        detector_class,
                        absolute_score / 100,
                    )

                    if zscore is None:
                        relative_defcon, relative_comment = None, None
                        relative_score = "n/a"

                    else:
                        relative_defcon, relative_comment = (
                            calibration.defcon_and_comment(zscore)
                        )
                        relative_score = f"{zscore:+.1f}"
                        calibration_used = True

                    absolute_defcon = map_score(absolute_score)
                    if absolute_score == 100.0:
                        relative_defcon, absolute_defcon = 5, 5
                    overall_severity = (
                        min(absolute_defcon, relative_defcon)
                        if isinstance(relative_defcon, int)
                        else absolute_defcon
                    )

                    probe_detector_result = {
                        "detector_name": detector,
                        "detector_descr": html.escape(detector_description),
                        "absolute_score": f"{absolute_score:.1f}%",
                        "absolute_defcon": absolute_defcon,
                        "absolute_comment": garak.analyze.ABSOLUTE_COMMENT[
                            absolute_defcon
                        ],
                        "zscore": relative_score,
                        "zscore_defcon": relative_defcon,
                        "zscore_comment": relative_comment,
                        "overall_severity": overall_severity,
                    }

                    report_digest["probe_group"][probe_group]["probes"][probe_plugin_name]["detectors"][detector]["name"] = dict(probe_detector_result)

                    if absolute_score < 100.0 or _config.reporting.show_100_pass_modules:
                        digest_content += detector_template.render(
                            probe_detector_result
                        )

        digest_content += end_module.render()

    conn.close()

    if calibration_used:
        calibration_date, calibration_model_count, calibration_model_list = "", "?", ""
        if calibration.metadata is not None:
            calibration_date = calibration.metadata["date"]
            calibration_models = calibration.metadata["filenames"]
            calibration_models = [
                s.replace(".report.jsonl", "") for s in calibration_models
            ]
            calibration_model_list = ", ".join(sorted(calibration_models))
            calibration_model_count = len(calibration_models)

        calibration_info = {
            "calibration_date": calibration_date,
            "model_count": calibration_model_count,
            "model_list": calibration_model_list,
        }
        report_digest["meta"]["calibration"]["info"] = calibration_info

        digest_content += about_z_template.render(calibration_info)

    digest_content += footer_template.render()

    return digest_content


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    report_path = sys.argv[1]
    taxonomy = None
    if len(sys.argv) == 3:
        taxonomy = sys.argv[2]
    digest_content = compile_digest(report_path, taxonomy=taxonomy)
    print(digest_content)
