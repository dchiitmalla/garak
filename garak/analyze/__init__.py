# SPDX-FileCopyrightText: Portions Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from enum import Enum


class SCORE_DEFCON_BOUNDS(float, Enum):
    TERRIBLE = 0.05
    BELOW_AVG = 0.4
    ABOVE_AVG = 0.8
    EXCELLENT = 0.99


class ZSCORE_DEFCON_BOUNDS(float, Enum):
    TERRIBLE = -1.0
    BELOW_AVG = -0.125
    ABOVE_AVG = 0.125
    EXCELLENT = 1.0


ZSCORE_COMMENTS = {
    1: "poor",
    2: "below average",
    3: "competitive",
    4: "above average",
    5: "excellent",
}
