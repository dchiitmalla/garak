# SPDX-FileCopyrightText: Portions Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from enum import IntEnum


class Tier(IntEnum):
    OF_CONCERN = 1
    COMPETE = 2
    INFORMATIONAL = 3
    UNLISTED = 9
