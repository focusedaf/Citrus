import time

from fpdf import FPDF


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

        return ", ".join(
            str(x)
            for x in value
        )

    if isinstance(value, dict):
        if not value:
            return "None detected"

        return ", ".join(
            f"{k}: {v}"
            for k, v in value.items()
        )

    return str(value)


def _short_address(address):
    if not address:
        return "Unknown"

    address = str(address)

    if len(address) <= 14:
        return address

    return f"{address[:7]}...{address[-5:]}"


def _short_number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "0"

    if number == 0:
        return "0"

    if abs(number) >= 1_000_000_000:
        return f"{number / 1_000_000_000:.2f}B"

    if abs(number) >= 1_000_000:
        return f"{number / 1_000_000:.2f}M"

    if abs(number) >= 1_000:
        return f"{number / 1_000:.2f}K"

    if abs(number) >= 1:
        return f"{number:.4f}".rstrip("0").rstrip(".")

    return f"{number:.8f}".rstrip("0").rstrip(".")


def _wallet_behavior_label(behavior):
    labels = {
        "suspect_wallet": "Suspect wallet",
        "hot_wallet": "Hot-wallet-like",
        "cold_wallet": "Cold-wallet-like",
        "intermediary": "Intermediary wallet",
        "wallet": "Wallet",
        "unknown": "Wallet - insufficient evidence",
    }

    return labels.get(
        behavior,
        str(behavior).replace("_", " ").title(),
    )


def _chain_label(chain_id, summary):
    chain = summary.get("chain")

    if chain:
        return chain

    chain_names = {
        1: "Ethereum",
        56: "BNB Smart Chain",
        137: "Polygon",
        42161: "Arbitrum One",
        10: "Optimism",
        43114: "Avalanche C-Chain",
        "1": "Ethereum",
        "56": "BNB Smart Chain",
        "137": "Polygon",
        "42161": "Arbitrum One",
        "10": "Optimism",
        "43114": "Avalanche C-Chain",
    }

    chain_id = summary.get("chain_id", chain_id)

    return chain_names.get(
        chain_id,
        f"Chain ID {chain_id}" if chain_id else "Unknown",
    )


class InvestigationReport(FPDF):

    def header(self):
        self.set_font(
            "Helvetica",
            "B",
            16,
        )

        self.cell(
            0,
            10,
            "CITRUS - Crypto Fraud Investigation Report",
            ln=True,
            align="C",
        )

        self.set_font(
            "Helvetica",
            "",
            9,
        )

        self.cell(
            0,
            6,
            _safe_text(
                f"Generated: "
                f"{time.strftime('%Y-%m-%d %H:%M:%S')}"
            ),
            ln=True,
            align="C",
        )

        self.ln(4)

    def footer(self):
        self.set_y(-15)

        self.set_font(
            "Helvetica",
            "",
            8,
        )

        self.cell(
            0,
            10,
            f"Page {self.page_no()}",
            align="C",
        )

    def section_title(self, title):
        self.set_font(
            "Helvetica",
            "B",
            12,
        )

        self.set_fill_color(
            230,
            230,
            230,
        )

        self.cell(
            0,
            8,
            _safe_text(title),
            ln=True,
            fill=True,
        )

        self.ln(2)

    def kv_row(self, key, value):
        self.set_font(
            "Helvetica",
            "B",
            10,
        )

        self.cell(
            55,
            7,
            _safe_text(key),
        )

        self.set_font(
            "Helvetica",
            "",
            10,
        )

        self.multi_cell(
            0,
            7,
            _safe_text(value),
        )

    def bullet(self, text):
        self.set_font(
            "Helvetica",
            "",
            10,
        )

        self.multi_cell(
            0,
            6,
            _safe_text(f"- {text}"),
        )

    def table_header(self, columns):
        self.set_font(
            "Helvetica",
            "B",
            9,
        )

        for label, width in columns:
            self.cell(
                width,
                7,
                _safe_text(label),
                border=1,
            )

        self.ln()

    def table_row(self, values):
        self.set_font(
            "Helvetica",
            "",
            8,
        )

        for value, width in values:
            self.cell(
                width,
                7,
                _safe_text(value),
                border=1,
            )

        self.ln()


def _render_wallet_classifications(pdf, summary):
    classifications = summary.get(
        "wallet_classifications",
        [],
    )

    if not classifications:
        pdf.bullet(
            "No wallet behavioral classifications were available."
        )
        return

    columns = [
        ("Address", 36),
        ("Classification", 45),
        ("Incoming", 22),
        ("Outgoing", 22),
        ("Confidence", 24),
        ("Reason", 51),
    ]

    pdf.table_header(columns)

    for item in classifications:
        address = _short_address(
            item.get("address")
        )

        behavior = _wallet_behavior_label(
            item.get("behavior", "unknown")
        )

        incoming = str(
            item.get(
                "incoming_transactions",
                0,
            )
        )

        outgoing = str(
            item.get(
                "outgoing_transactions",
                0,
            )
        )

        confidence = item.get(
            "confidence"
        )

        if confidence is None:
            confidence_text = "N/A"
        else:
            try:
                confidence_text = (
                    f"{float(confidence) * 100:.0f}%"
                )
            except (TypeError, ValueError):
                confidence_text = str(confidence)

        reasons = item.get(
            "reasons",
            [],
        )

        reason = (
            reasons[0]
            if isinstance(reasons, list) and reasons
            else "Behavioral evidence unavailable."
        )

        pdf.table_row(
            [
                (address, 36),
                (behavior, 45),
                (incoming, 22),
                (outgoing, 22),
                (confidence_text, 24),
                (reason[:70], 51),
            ]
        )


def _render_flow_paths(pdf, summary):
    paths = summary.get(
        "flow_paths",
        [],
    )

    if not paths:
        pdf.bullet(
            "No meaningful value-flow path was derived from the traced data."
        )
        return

    for path in paths[:10]:
        pdf.bullet(path)


def _render_entity_list(pdf, label, value):
    if value is None:
        return

    if isinstance(value, list):
        if not value:
            pdf.kv_row(
                f"{label}:",
                "None detected",
            )
            return

        pdf.kv_row(
            f"{label}:",
            _as_text(value),
        )
        return

    pdf.kv_row(
        f"{label}:",
        _as_text(value),
    )


def generate_pdf_report(
    summary,
    risk,
    trace_id=None,
    evidence=None,
):
    summary = summary or {}
    risk = risk or {}

    pdf = InvestigationReport()

    pdf.set_auto_page_break(
        auto=True,
        margin=20,
    )

    pdf.add_page()


    pdf.section_title(
        "Case Overview"
    )

    pdf.kv_row(
        "Trace ID:",
        (
            str(trace_id)
            if trace_id is not None
            else "N/A"
        ),
    )

    pdf.kv_row(
        "Reported Address:",
        summary.get(
            "reported_address",
            summary.get(
                "address",
                "Unknown",
            ),
        ),
    )

    pdf.kv_row(
        "Chain:",
        _chain_label(
            summary.get("chain_id"),
            summary,
        ),
    )

    pdf.kv_row(
        "Chain ID:",
        str(
            summary.get(
                "chain_id",
                "Unknown",
            )
        ),
    )

    pdf.kv_row(
        "Transactions Analyzed:",
        str(
            summary.get(
                "transactions_analyzed",
                0,
            )
        ),
    )

    pdf.kv_row(
        "Graph Nodes:",
        str(
            summary.get(
                "nodes",
                0,
            )
        ),
    )

    pdf.kv_row(
        "Graph Connections:",
        str(
            summary.get(
                "edges",
                0,
            )
        ),
    )

    pdf.kv_row(
        "Value-Flow Connections:",
        str(
            summary.get(
                "value_edges",
                summary.get(
                    "edges",
                    0,
                ),
            )
        ),
    )

    pdf.kv_row(
        "Contract Interactions:",
        str(
            summary.get(
                "interaction_edges",
                0,
            )
        ),
    )

    pdf.kv_row(
        "Wallets Observed:",
        str(
            summary.get(
                "wallets",
                0,
            )
        ),
    )

    pdf.kv_row(
        "Known VASPs / Exchanges:",
        str(
            summary.get(
                "exchanges",
                0,
            )
        ),
    )

    pdf.kv_row(
        "Bridges:",
        str(
            summary.get(
                "bridges",
                0,
            )
        ),
    )

    pdf.kv_row(
        "Contracts:",
        str(
            summary.get(
                "contracts",
                0,
            )
        ),
    )

    pdf.kv_row(
        "Assets Observed:",
        _as_text(
            summary.get(
                "assets_observed",
                [],
            )
        ),
    )

    pdf.ln(3)

   

    risk_label = risk.get(
        "label",
        "Rule-Based Risk Indicator",
    )

    pdf.section_title(
        f"Risk Assessment - {risk_label}"
    )

    pdf.kv_row(
        "Risk Score:",
        f"{risk.get('score', 0)} / 100",
    )

    pdf.kv_row(
        "Risk Level:",
        risk.get(
            "level",
            "Low",
        ),
    )

    reasons = risk.get(
        "reasons",
        [],
    )

    if reasons:
        pdf.ln(2)

        pdf.set_font(
            "Helvetica",
            "B",
            10,
        )

        pdf.cell(
            0,
            7,
            "Triggered Indicators:",
            ln=True,
        )

        for reason in reasons:
            pdf.bullet(reason)

    else:
        pdf.bullet(
            "No risk indicators were triggered."
        )

    pdf.ln(3)

   

    metrics = risk.get(
        "metrics",
        {},
    )

    if metrics:
        pdf.section_title(
            "Risk Metrics"
        )

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
                    "Yes"
                    if metrics[key]
                    else "No",
                )

        pdf.ln(3)

  

    pdf.section_title(
        "Observed Fund Flow"
    )

    pdf.bullet(
        "The following paths are derived from value-transfer edges "
        "rather than generic contract interactions."
    )

    _render_flow_paths(
        pdf,
        summary,
    )

    pdf.ln(3)

   

    pdf.section_title(
        "Wallet Behavioral Classification"
    )

    pdf.multi_cell(
        0,
        5,
        _safe_text(
            "Wallet classifications are behavioral inferences based "
            "on the activity visible in the traced blockchain data. "
            "They do not establish the physical storage method of a "
            "private key. In particular, hot-wallet-like and "
            "cold-wallet-like indicate observed activity patterns."
        ),
    )

    pdf.ln(3)

    _render_wallet_classifications(
        pdf,
        summary,
    )

    pdf.ln(3)

    

    pdf.section_title(
        "Entity Findings"
    )

    entity_findings = summary.get(
        "entity_findings",
        {},
    )

    _render_entity_list(
        pdf,
        "VASP / Exchange",
        entity_findings.get(
            "vasp",
            summary.get(
                "vasps",
                summary.get(
                    "exchanges",
                    None,
                ),
            ),
        ),
    )

    _render_entity_list(
        pdf,
        "Bridge",
        entity_findings.get(
            "bridge",
            summary.get(
                "bridges",
                None,
            ),
        ),
    )

    _render_entity_list(
        pdf,
        "Mixer",
        entity_findings.get(
            "mixer",
            summary.get(
                "mixers",
                None,
            ),
        ),
    )

    _render_entity_list(
        pdf,
        "Known Contracts",
        entity_findings.get(
            "known_contracts",
            summary.get(
                "known_contracts",
                None,
            ),
        ),
    )

    unidentified_wallets = entity_findings.get(
        "unidentified_wallets",
        summary.get(
            "unknown_entities",
            0,
        ),
    )

    pdf.kv_row(
        "Unidentified / Unknown Entities:",
        str(unidentified_wallets),
    )

    pdf.ln(3)

    

    pdf.section_title(
        "Asset Activity"
    )

    asset_totals = summary.get(
        "asset_totals",
        {},
    )

    if asset_totals:
        for asset, amount in asset_totals.items():
            pdf.bullet(
                f"{asset}: {_short_number(amount)}"
            )
    else:
        pdf.bullet(
            "No transferred asset totals were available."
        )

    pdf.ln(3)

   

    pdf.section_title(
        "Spoofed / Lookalike Tokens"
    )

    spoofed_tokens = summary.get(
        "spoofed_tokens_detected"
    )

    pdf.bullet(
        _as_text(
            spoofed_tokens
        )
    )

    pdf.ln(3)

   

    pdf.section_title(
        "Cross-Chain Activity"
    )

    cross_chain = summary.get(
        "cross_chain_activity",
        summary.get(
            "cross_chain",
            {},
        ),
    )

    pdf.bullet(
        _as_text(
            cross_chain
        )
    )

    pdf.ln(3)


    if evidence:
        pdf.section_title(
            "Evidence & Chain of Custody"
        )

        pdf.kv_row(
            "Evidence bundle:",
            evidence.get(
                "filename",
                "N/A",
            ),
        )

        pdf.kv_row(
            "SHA-256 hash:",
            evidence.get(
                "hash",
                "N/A",
            ),
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
                "This hash covers the raw source-API records and "
                "derived transaction edges used to generate this "
                "investigation output. Re-hashing the stored evidence "
                "bundle and comparing it against this value can "
                "identify modifications made after generation."
            ),
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
            "risk and attribution system. Wallet behavioral "
            "classifications are inferred from observable blockchain "
            "activity and should not be interpreted as proof of the "
            "physical storage method, ownership, or criminal "
            "liability of an address. Findings are intended to assist "
            "investigators and should be independently verified."
        ),
    )

    output = pdf.output(
        dest="S"
    )

    return output.encode(
        "latin-1"
    )