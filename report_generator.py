import os
import time
from fpdf import FPDF
from config import REPORTS_DIR


def _safe_text(value):
  
    return (
        str(value)
        .encode("latin-1", errors="replace")
        .decode("latin-1")
    )


def _as_text(value):

    if value is None:
        return "None detected"

    if isinstance(value, list):
        if not value:
            return "None detected"
        return ", ".join(str(x) for x in value)

    if isinstance(value, dict):
        return ", ".join(f"{k}: {v}" for k, v in value.items())

    return str(value)


class InvestigationReport(FPDF):

    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.cell(
            0,
            10,
            "CITRUS - Crypto Fraud Investigation Report",
            ln=True,
            align="C",
        )

        self.set_font("Helvetica", "", 9)
        self.cell(
            0,
            6,
            _safe_text(
                f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}"
            ),
            ln=True,
            align="C",
        )

        self.ln(4)

    def footer(self):
        self.set_y(-15)

        self.set_font("Helvetica", "", 8)

        self.cell(
            0,
            10,
            f"Page {self.page_no()}",
            align="C",
        )

    def section_title(self, title):
        self.set_font("Helvetica", "B", 12)
        self.set_fill_color(230, 230, 230)

        self.cell(
            0,
            8,
            _safe_text(title),
            ln=True,
            fill=True,
        )

        self.ln(2)

    def kv_row(self, key, value):
        self.set_font("Helvetica", "B", 10)

        self.cell(
            55,
            7,
            _safe_text(key),
        )

        self.set_font("Helvetica", "", 10)

        self.multi_cell(
            0,
            7,
            _safe_text(value),
        )

    def bullet(self, text):
        self.set_font("Helvetica", "", 10)

        self.multi_cell(
            0,
            6,
            _safe_text(f"- {text}"),
        )


def generate_pdf_report(
    summary,
    risk,
    trace_id=None,
    output_path=None,
):
  
    os.makedirs(REPORTS_DIR, exist_ok=True)

    if output_path is None:

        if trace_id is not None:
            filename = f"report_{trace_id}.pdf"
        else:
            safe_addr = str(
                summary.get("reported_address", "unknown")
            )[:10]

            filename = (
                f"report_{safe_addr}_{int(time.time())}.pdf"
            )

        output_path = os.path.join(
            REPORTS_DIR,
            filename,
        )

    pdf = InvestigationReport()

    pdf.set_auto_page_break(
        auto=True,
        margin=20,
    )

    pdf.add_page()

   

    pdf.section_title("Case Overview")

    pdf.kv_row(
        "Trace ID:",
        str(trace_id) if trace_id is not None else "N/A",
    )

    pdf.kv_row(
        "Reported Address:",
        summary.get("reported_address", "Unknown"),
    )

    pdf.kv_row(
        "Chain:",
        summary.get("chain", "Unknown"),
    )

    pdf.kv_row(
        "Transactions Analyzed:",
        str(summary.get("transactions_analyzed", 0)),
    )

    pdf.kv_row(
        "Unique Counterparties:",
        str(summary.get("unique_counterparties", 0)),
    )

    pdf.kv_row(
        "Maximum Trace Depth:",
        f"{summary.get('max_trace_depth', 0)} hop(s)",
    )

    pdf.kv_row(
        "Assets Observed:",
        _as_text(summary.get("assets_observed")),
    )

    pdf.ln(3)

   

    pdf.section_title(
        f"Risk Assessment - "
        f"{risk.get('label', 'Rule-Based Risk Indicator')}"
    )

    pdf.kv_row(
        "Risk Score:",
        f"{risk.get('score', 0)} / 100",
    )

    pdf.kv_row(
        "Risk Level:",
        risk.get("level", "Low"),
    )

    reasons = risk.get("reasons", [])

    if reasons:
        pdf.ln(2)

        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(
            0,
            7,
            "Triggered Indicators:",
            ln=True,
        )

        for reason in reasons:
            pdf.bullet(reason)
    else:
        pdf.bullet("No risk indicators triggered.")

    pdf.ln(3)

   

    metrics = risk.get("metrics", {})

    if metrics:

        pdf.section_title("Risk Metrics")

        metric_labels = {
            "transaction_count": "Transaction Count",
            "unique_counterparties": "Unique Counterparties",
            "unique_hops": "Trace Depth",
            "fan_out": "Fan-Out",
            "fan_in": "Fan-In",
            "spoofed_token_count": "Spoofed Token Transfers",
            "rapid_movement_node_count": "Rapid Movement Nodes",
        }

        for key, label in metric_labels.items():

            if key in metrics:
                pdf.kv_row(
                    f"{label}:",
                    str(metrics[key]),
                )

        boolean_metrics = {
            "mixer_exposure": "Mixer Exposure",
            "bridge_exposure": "Bridge Exposure",
            "vasp_exposure": "VASP Exposure",
            "large_value_transfer": "Large Value Transfer",
            "spoofed_token_detected": "Spoofed Token Detected",
            "rapid_movement_detected": "Rapid Movement Detected",
            "cross_chain_activity": "Cross-Chain Activity",
        }

        for key, label in boolean_metrics.items():

            if key in metrics:
                pdf.kv_row(
                    f"{label}:",
                    "Yes" if metrics[key] else "No",
                )

        pdf.ln(3)

  

    pdf.section_title("Entity Findings")

    entity_findings = summary.get(
        "entity_findings",
        {},
    )

    pdf.kv_row(
        "VASP:",
        _as_text(entity_findings.get("vasp")),
    )

    pdf.kv_row(
        "Bridge:",
        _as_text(entity_findings.get("bridge")),
    )

    pdf.kv_row(
        "Mixer:",
        _as_text(entity_findings.get("mixer")),
    )

    pdf.kv_row(
        "Known Contracts:",
        _as_text(
            entity_findings.get("known_contracts")
        ),
    )

    pdf.kv_row(
        "Unidentified Wallets:",
        str(
            entity_findings.get(
                "unidentified_wallets",
                0,
            )
        ),
    )

    pdf.ln(3)

    pdf.section_title(
        "Spoofed / Lookalike Tokens"
    )

    spoofed = summary.get(
        "spoofed_tokens_detected"
    )

    pdf.bullet(
        _as_text(spoofed)
    )

    pdf.ln(3)


    pdf.section_title(
        "Cross-Chain Activity"
    )

    cross_chain = summary.get(
        "cross_chain_activity"
    )

    pdf.bullet(
        _as_text(cross_chain)
    )

    pdf.ln(3)


    pdf.section_title(
        "Investigation Disclaimer"
    )

    pdf.set_font(
        "Helvetica",
        "I",
        8,
    )

    pdf.multi_cell(
        0,
        5,
        _safe_text(
            "This report is generated by a rule-based prototype "
            "risk indicator. It is not a certified fraud-detection "
            "model and does not establish criminal liability. "
            "The findings are intended to assist investigators "
            "and should be independently verified."
        ),
    )

    pdf.output(output_path)

    return output_path