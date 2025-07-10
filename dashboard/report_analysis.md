# Understanding Garak Reports and BigQuery Integration

This document provides a guide to interpreting the `garak` HTML security report and explains how its components map to the fields in the persistent BigQuery table. This allows for powerful, data-driven analysis of your LLM's security posture.

## 1. Anatomy of the Garak HTML Report

The HTML report is a human-readable summary of a `garak` scan. It's organized hierarchically to help you quickly identify areas of high risk.

-   **Report Header**: At the top, you'll find metadata about the scan, including the **model name**, the **garak version** used, and the **time** the scan was run.
-   **Probe Groups**: The report is divided into collapsible sections, each representing a **Probe Group**. A group is a collection of related tests. This grouping can be based on the probe's Python module (e.g., all probes in `snowball.py`) or a formal taxonomy like the `OWASP LLM Top 10`.
-   **Probes**: Within each group are the individual **Probes**. A probe is a specific test designed to elicit a certain type of vulnerability (e.g., `dan.Dan_6_0` is a specific DAN prompt).
-   **Detectors**: This is the most granular level. A **Detector** is the component that evaluates the model's output for a given prompt and determines if it passed or failed. A single probe can have multiple detectors.

### Key Metrics in the Report

For each test, you will see several metrics:

-   **Score (%)**: The percentage of prompts that successfully passed the detector's check. **A lower score is worse**, indicating more failures.
-   **DEFCON (Absolute)**: A 1-5 severity rating based on the raw score. **1 is the most severe (many failures)**, and 5 is the best (few or no failures).
-   **z-score (Relative)**: A statistical measure of how the model performed compared to a pre-computed baseline of other models. It represents the number of standard deviations the model's score is from the baseline mean. A large negative z-score (e.g., -2.5) indicates the model performed significantly worse than average for this test.
-   **DEFCON (Relative)**: A 1-5 severity rating based on the z-score. **1 is the most severe (much worse than average)**.
-   **Final DEFCON**: The ultimate severity rating for the test, which intelligently combines the absolute and relative DEFCON scores to give the most complete picture of the risk.

## 2. Mapping HTML Report Data to BigQuery

The true power of `garak` comes from analyzing its raw output. The ETL script populates a BigQuery table where each row represents a single detector's result for a single probe. Here is how the visual report elements map to that table's schema.

| HTML Report Element | Corresponding BigQuery Field(s) | Notes |
| :--- | :--- | :--- |
| **Overall Run Info** | | |
| Model Name & Type | `model_name`, `model_type` | Identifies the model under test. |
| Run Time & UUID | `start_time`, `run_uuid` | Tracks when the scan was run. |
| **Group Level** | | |
| Probe Group Name | `probe_group` | The name of the category (e.g., `dan`, `owasp:llm01`). |
| **Probe Level** | | |
| Probe Name | `probe_module`, `probe_class` | The full name of the test probe. |
| Probe Description | `probe_descr` | The docstring explaining what the probe does. |
| Probe Tags & Tier | `probe_tags`, `probe_tier` | Metadata for advanced filtering and analysis. |
| **Detector Level** | | |
| Detector Name | `detector_module`, `detector_class` | The full name of the evaluation component. |
| Pass/Total Counts | `passed_count`, `total_count` | The raw numbers behind the pass rate. |
| **Calculated Metrics** | | |
| Score (%) | `pass_rate` | The core pass/fail metric (0.0 to 1.0). |
| Absolute DEFCON | `absolute_defcon` | The 1-5 score based on `pass_rate`. |
| z-score | `z_score` | The powerful relative performance score. NULL if no baseline exists. |
| Relative DEFCON | `relative_defcon` | The 1-5 score based on `z_score`. NULL if no baseline exists. |
| Final DEFCON | `final_defcon` | The final, combined severity rating for the test. |

## 3. Example BigQuery Use Cases

With this data, you can move beyond static reports and perform powerful, longitudinal analysis.

**Example 1: Find the top 10 worst-performing tests for a specific model.**

```sql
SELECT
  probe_class,
  detector_class,
  pass_rate,
  final_defcon
FROM
  `your_dataset.garak_results`
WHERE
  model_name = 'your-model-name'
ORDER BY
  final_defcon ASC, pass_rate ASC
LIMIT 10;
```

**Example 2: Track the performance on DAN prompts over time for all models.**

```sql
SELECT
  model_name,
  start_time,
  pass_rate
FROM
  `your_dataset.garak_results`
WHERE
  probe_group = 'dan'
ORDER BY
  start_time DESC;
```
