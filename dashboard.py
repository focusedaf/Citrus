
import html
import json
import time
from db import (
    get_all_traces,
    get_all_alerts,
    get_trace_by_id,
)


RISK_COLORS = {
    "Low": "#2ecc71",
    "Medium": "#f1c40f",
    "High": "#e67e22",
    "Critical": "#e74c3c",
}


def esc(value):
  
    return html.escape(str(value))


def format_timestamp(timestamp):
    if not timestamp:
        return "Unknown"

    try:
        return time.strftime(
            "%Y-%m-%d %H:%M:%S",
            time.localtime(int(timestamp)),
        )
    except Exception:
        return "Unknown"


def format_list(value):
    if value is None:
        return "None detected"

    if isinstance(value, list):

        if not value:
            return "None detected"

        return ", ".join(
            str(item)
            for item in value
        )

    return str(value)


def generate_dashboard_html():
    
    traces = get_all_traces(limit=50)
    alerts = get_all_alerts(limit=50)

    total_traces = len(traces)

    high_risk = sum(
        1
        for trace in traces
        if trace.get("risk_level")
        in ("High", "Critical")
    )

    critical_count = sum(
        1
        for trace in traces
        if trace.get("risk_level") == "Critical"
    )

    total_alerts = len(alerts)

    rows_html = ""

    for trace in traces:

        trace_id = trace["id"]
        address = trace.get(
            "address",
            "Unknown",
        )

        risk_level = trace.get(
            "risk_level",
            "Low",
        )

        risk_score = trace.get(
            "risk_score",
            0,
        )

        chain_id = trace.get(
            "chain_id",
            "?",
        )

        created_at = format_timestamp(
            trace.get("created_at")
        )

        color = RISK_COLORS.get(
            risk_level,
            "#3498db",
        )

        rows_html += f"""
        <tr>

            <td>
                <a class="trace-id"
                   href="/dashboard/trace/{trace_id}">
                    #{trace_id}
                </a>
            </td>

            <td>
                <code>{esc(address)}</code>
            </td>

            <td>
                {esc(chain_id)}
            </td>

            <td>
                <span class="risk"
                      style="color:{color};">
                    {esc(risk_level)}
                </span>
            </td>

            <td>
                <strong>{esc(risk_score)}</strong>/100
            </td>

            <td>
                {esc(created_at)}
            </td>

            <td class="actions">

                <a href="/dashboard/trace/{trace_id}">
                    View
                </a>

                <a href="/report/{trace_id}"
                   target="_blank">
                    PDF
                </a>

                <a href="/graph"
                   target="_blank">
                    Graph
                </a>

            </td>

        </tr>
        """

    if not rows_html:
        rows_html = """
        <tr>
            <td colspan="7"
                class="empty">
                No traces yet.
                Run /trace on a wallet address.
            </td>
        </tr>
        """

    alerts_html = ""

    for alert in alerts:

        risk_level = alert.get(
            "risk_level",
            "Low",
        )

        color = RISK_COLORS.get(
            risk_level,
            "#3498db",
        )

        trace_id = alert.get(
            "trace_id"
        )

        trace_link = ""

        if trace_id:
            trace_link = (
                f'<a href="/dashboard/trace/{trace_id}">'
                f"Trace #{trace_id}"
                f"</a>"
            )

        alerts_html += f"""
        <div class="alert">

            <div>
                <span class="risk"
                      style="color:{color};">
                    [{esc(risk_level)}]
                </span>

                {trace_link}
            </div>

            <div class="alert-address">
                <code>
                    {esc(alert.get("address", ""))}
                </code>
            </div>

            <div class="alert-message">
                {esc(alert.get("message", ""))}
            </div>

            <div class="alert-time">
                {esc(
                    format_timestamp(
                        alert.get("created_at")
                    )
                )}
            </div>

        </div>
        """

    if not alerts_html:
        alerts_html = """
        <div class="empty">
            No alerts raised yet.
        </div>
        """

    html_page = f"""
<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>CITRUS - Investigation Dashboard</title>

<style>

* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    padding: 32px;
    background: #111;
    color: #eee;
    font-family:
        Inter,
        ui-sans-serif,
        system-ui,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
}}

.container {{
    max-width: 1500px;
    margin: auto;
}}

.header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 28px;
}}

.brand {{
    font-size: 28px;
    font-weight: 700;
}}

.subtitle {{
    color: #888;
    margin-top: 5px;
}}

.refresh {{
    padding: 9px 15px;
    border: 1px solid #444;
    border-radius: 7px;
    color: #ddd;
    text-decoration: none;
    background: #1c1c1c;
}}

.refresh:hover {{
    background: #292929;
}}

.stats {{
    display: grid;
    grid-template-columns:
        repeat(4, minmax(0, 1fr));
    gap: 16px;
    margin-bottom: 30px;
}}

.stat {{
    background: #191919;
    border: 1px solid #303030;
    border-radius: 10px;
    padding: 20px;
}}

.stat-label {{
    color: #888;
    font-size: 13px;
    margin-bottom: 8px;
}}

.stat-value {{
    font-size: 30px;
    font-weight: 700;
}}

.card {{
    background: #171717;
    border: 1px solid #303030;
    border-radius: 10px;
    margin-bottom: 24px;
    overflow: hidden;
}}

.card-header {{
    padding: 18px 20px;
    border-bottom: 1px solid #303030;
}}

.card-header h2 {{
    margin: 0;
    font-size: 17px;
}}

.table-wrapper {{
    overflow-x: auto;
}}

table {{
    width: 100%;
    border-collapse: collapse;
}}

th {{
    text-align: left;
    padding: 13px 16px;
    background: #1d1d1d;
    color: #999;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: .04em;
}}

td {{
    padding: 15px 16px;
    border-top: 1px solid #292929;
    vertical-align: middle;
}}

tr:hover {{
    background: #1c1c1c;
}}

code {{
    color: #cfcfcf;
    font-family:
        "SFMono-Regular",
        Consolas,
        monospace;
    font-size: 12px;
}}

.trace-id {{
    color: #6cb6ff;
    text-decoration: none;
    font-weight: 600;
}}

.trace-id:hover {{
    text-decoration: underline;
}}

.risk {{
    font-weight: 700;
}}

.actions {{
    white-space: nowrap;
}}

.actions a {{
    color: #6cb6ff;
    text-decoration: none;
    margin-right: 12px;
    font-size: 13px;
}}

.actions a:hover {{
    text-decoration: underline;
}}

.alert {{
    padding: 18px 20px;
    border-bottom: 1px solid #292929;
}}

.alert:last-child {{
    border-bottom: none;
}}

.alert-address {{
    margin-top: 7px;
}}

.alert-message {{
    margin-top: 8px;
    color: #ccc;
    line-height: 1.5;
}}

.alert-time {{
    margin-top: 8px;
    color: #666;
    font-size: 12px;
}}

.alert a {{
    color: #6cb6ff;
    text-decoration: none;
}}

.empty {{
    padding: 30px;
    text-align: center;
    color: #777;
}}

@media (max-width: 900px) {{

    body {{
        padding: 18px;
    }}

    .stats {{
        grid-template-columns:
            repeat(2, minmax(0, 1fr));
    }}

}}

</style>

</head>

<body>

<div class="container">

    <div class="header">

        <div>
            <div class="brand">
                CITRUS
            </div>

            <div class="subtitle">
                Crypto Fraud Investigation Dashboard
            </div>
        </div>

        <a class="refresh"
           href="/dashboard">
            ↻ Refresh
        </a>

    </div>


    <div class="stats">

        <div class="stat">
            <div class="stat-label">
                Total Traces
            </div>

            <div class="stat-value">
                {total_traces}
            </div>
        </div>


        <div class="stat">
            <div class="stat-label">
                High / Critical
            </div>

            <div class="stat-value">
                {high_risk}
            </div>
        </div>


        <div class="stat">
            <div class="stat-label">
                Critical
            </div>

            <div class="stat-value">
                {critical_count}
            </div>
        </div>


        <div class="stat">
            <div class="stat-label">
                Alerts
            </div>

            <div class="stat-value">
                {total_alerts}
            </div>
        </div>

    </div>


    <div class="card">

        <div class="card-header">

            <h2>
                Recent Investigations
            </h2>

        </div>

        <div class="table-wrapper">

            <table>

                <thead>

                    <tr>
                        <th>ID</th>
                        <th>Wallet</th>
                        <th>Chain</th>
                        <th>Risk</th>
                        <th>Score</th>
                        <th>Created</th>
                        <th>Actions</th>
                    </tr>

                </thead>

                <tbody>

                    {rows_html}

                </tbody>

            </table>

        </div>

    </div>


    <div class="card">

        <div class="card-header">

            <h2>
                Recent Alerts
            </h2>

        </div>

        {alerts_html}

    </div>

</div>

</body>

</html>
"""

    return html_page


def generate_trace_detail_html(trace):
   
    if not trace:
        return """
        <html>
        <body style="
            background:#111;
            color:#eee;
            font-family:Arial;
            padding:40px;
        ">
            <h1>Trace not found</h1>
            <a href="/dashboard">Back to dashboard</a>
        </body>
        </html>
        """

    trace_id = trace["id"]

    address = trace.get(
        "address",
        "Unknown",
    )

    chain_id = trace.get(
        "chain_id",
        "Unknown",
    )

    risk_level = trace.get(
        "risk_level",
        "Low",
    )

    risk_score = trace.get(
        "risk_score",
        0,
    )

    summary = trace.get(
        "summary_json"
    ) or {}

    edges = trace.get(
        "edges_json"
    ) or []

    color = RISK_COLORS.get(
        risk_level,
        "#3498db",
    )

    assets = format_list(
        summary.get("assets_observed")
    )

    indicators = summary.get(
        "risk_indicators",
        [],
    )

    indicators_html = ""

    for indicator in indicators:

        indicators_html += f"""
        <li>
            {esc(indicator)}
        </li>
        """

    if not indicators_html:
        indicators_html = """
        <li>No risk indicators triggered.</li>
        """

    entity_findings = summary.get(
        "entity_findings",
        {},
    )

    def entity_value(key):
        return esc(
            format_list(
                entity_findings.get(key)
            )
        )

    spoofed = format_list(
        summary.get(
            "spoofed_tokens_detected"
        )
    )

    cross_chain = format_list(
        summary.get(
            "cross_chain_activity"
        )
    )

    transaction_rows = ""

    # Show up to 100 stored edges.
    for edge in edges[:100]:

        transaction_rows += f"""
        <tr>

            <td>
                {esc(edge.get("hop", "-"))}
            </td>

            <td>
                <code>
                    {esc(edge.get("from", ""))}
                </code>
            </td>

            <td>
                <code>
                    {esc(edge.get("to", ""))}
                </code>
            </td>

            <td>
                {esc(edge.get("type", ""))}
            </td>

            <td>
                {esc(edge.get("amount", ""))}
                {esc(edge.get("token", ""))}
            </td>

            <td>
                <code>
                    {esc(edge.get("tx_hash", ""))}
                </code>
            </td>

        </tr>
        """

    if not transaction_rows:
        transaction_rows = """
        <tr>
            <td colspan="6"
                class="empty">
                No transaction edges stored.
            </td>
        </tr>
        """

    return f"""
<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>
CITRUS - Trace #{trace_id}
</title>

<style>

body {{
    margin: 0;
    padding: 32px;
    background: #111;
    color: #eee;
    font-family:
        Inter,
        system-ui,
        -apple-system,
        "Segoe UI",
        sans-serif;
}}

.container {{
    max-width: 1500px;
    margin: auto;
}}

.back {{
    color: #6cb6ff;
    text-decoration: none;
}}

.header {{
    margin: 22px 0 28px;
}}

.header h1 {{
    margin: 0;
    font-size: 28px;
}}

.address {{
    margin-top: 10px;
    color: #aaa;
    word-break: break-all;
}}

.actions {{
    margin-top: 20px;
}}

.actions a {{
    display: inline-block;
    padding: 10px 15px;
    margin-right: 8px;
    border: 1px solid #444;
    border-radius: 7px;
    color: #ddd;
    text-decoration: none;
    background: #1c1c1c;
}}

.actions a:hover {{
    background: #292929;
}}

.grid {{
    display: grid;
    grid-template-columns:
        repeat(4, minmax(0, 1fr));
    gap: 15px;
    margin-bottom: 24px;
}}

.card {{
    background: #171717;
    border: 1px solid #303030;
    border-radius: 10px;
    overflow: hidden;
    margin-bottom: 24px;
}}

.card-header {{
    padding: 17px 20px;
    border-bottom: 1px solid #303030;
}}

.card-header h2 {{
    margin: 0;
    font-size: 17px;
}}

.stat {{
    background: #191919;
    border: 1px solid #303030;
    border-radius: 10px;
    padding: 20px;
}}

.label {{
    color: #888;
    font-size: 12px;
    margin-bottom: 7px;
}}

.value {{
    font-size: 23px;
    font-weight: 700;
}}

.content {{
    padding: 20px;
}}

.risk {{
    color: {color};
    font-weight: 800;
}}

ul {{
    line-height: 1.8;
}}

.findings {{
    display: grid;
    grid-template-columns:
        repeat(2, minmax(0, 1fr));
    gap: 15px;
}}

.finding {{
    background: #1d1d1d;
    padding: 15px;
    border-radius: 8px;
}}

.finding-label {{
    color: #888;
    font-size: 12px;
    margin-bottom: 5px;
}}

table {{
    width: 100%;
    border-collapse: collapse;
}}

.wrapper {{
    overflow-x: auto;
}}

th {{
    padding: 12px;
    background: #1d1d1d;
    color: #888;
    text-align: left;
    font-size: 12px;
}}

td {{
    padding: 12px;
    border-top: 1px solid #292929;
    font-size: 13px;
}}

code {{
    font-family:
        "SFMono-Regular",
        Consolas,
        monospace;
    font-size: 11px;
    word-break: break-all;
    color: #ccc;
}}

.empty {{
    padding: 30px;
    text-align: center;
    color: #777;
}}

@media (max-width: 900px) {{

    body {{
        padding: 18px;
    }}

    .grid {{
        grid-template-columns:
            repeat(2, minmax(0, 1fr));
    }}

    .findings {{
        grid-template-columns: 1fr;
    }}

}}

</style>

</head>

<body>

<div class="container">

    <a class="back"
       href="/dashboard">
        ← Back to dashboard
    </a>


    <div class="header">

        <h1>
            Investigation #{trace_id}
        </h1>

        <div class="address">
            <code>{esc(address)}</code>
        </div>

        <div class="actions">

            <a href="/report/{trace_id}"
               target="_blank">
                View PDF Report
            </a>

            <a href="/graph"
               target="_blank">
                Open Transaction Graph
            </a>

        </div>

    </div>


    <div class="grid">

        <div class="stat">

            <div class="label">
                Risk Level
            </div>

            <div class="value risk">
                {esc(risk_level)}
            </div>

        </div>


        <div class="stat">

            <div class="label">
                Risk Score
            </div>

            <div class="value">
                {esc(risk_score)} / 100
            </div>

        </div>


        <div class="stat">

            <div class="label">
                Transactions
            </div>

            <div class="value">
                {esc(
                    summary.get(
                        "transactions_analyzed",
                        len(edges)
                    )
                )}
            </div>

        </div>


        <div class="stat">

            <div class="label">
                Trace Depth
            </div>

            <div class="value">
                {esc(
                    summary.get(
                        "max_trace_depth",
                        0
                    )
                )} hops
            </div>

        </div>

    </div>


    <div class="card">

        <div class="card-header">
            <h2>Case Overview</h2>
        </div>

        <div class="content">

            <div class="findings">

                <div class="finding">
                    <div class="finding-label">
                        Chain
                    </div>

                    {esc(
                        summary.get(
                            "chain",
                            chain_id
                        )
                    )}
                </div>


                <div class="finding">
                    <div class="finding-label">
                        Unique Counterparties
                    </div>

                    {esc(
                        summary.get(
                            "unique_counterparties",
                            0
                        )
                    )}
                </div>


                <div class="finding">
                    <div class="finding-label">
                        Assets Observed
                    </div>

                    {esc(assets)}
                </div>


                <div class="finding">
                    <div class="finding-label">
                        Cross-Chain Activity
                    </div>

                    {esc(cross_chain)}
                </div>

            </div>

        </div>

    </div>


    <div class="card">

        <div class="card-header">
            <h2>Risk Indicators</h2>
        </div>

        <div class="content">

            <ul>
                {indicators_html}
            </ul>

        </div>

    </div>


    <div class="card">

        <div class="card-header">
            <h2>Entity Findings</h2>
        </div>

        <div class="content">

            <div class="findings">

                <div class="finding">
                    <div class="finding-label">
                        VASP
                    </div>

                    {entity_value("vasp")}
                </div>


                <div class="finding">
                    <div class="finding-label">
                        Bridge
                    </div>

                    {entity_value("bridge")}
                </div>


                <div class="finding">
                    <div class="finding-label">
                        Mixer
                    </div>

                    {entity_value("mixer")}
                </div>


                <div class="finding">
                    <div class="finding-label">
                        Known Contracts
                    </div>

                    {entity_value("known_contracts")}
                </div>


                <div class="finding">
                    <div class="finding-label">
                        Unidentified Wallets
                    </div>

                    {esc(
                        entity_findings.get(
                            "unidentified_wallets",
                            0
                        )
                    )}
                </div>


                <div class="finding">
                    <div class="finding-label">
                        Spoofed / Lookalike Tokens
                    </div>

                    {esc(spoofed)}
                </div>

            </div>

        </div>

    </div>


    <div class="card">

        <div class="card-header">

            <h2>
                Transactions
                ({len(edges)})
            </h2>

        </div>

        <div class="wrapper">

            <table>

                <thead>

                    <tr>
                        <th>Hop</th>
                        <th>From</th>
                        <th>To</th>
                        <th>Type</th>
                        <th>Amount</th>
                        <th>Transaction Hash</th>
                    </tr>

                </thead>

                <tbody>

                    {transaction_rows}

                </tbody>

            </table>

        </div>

    </div>

</div>

</body>

</html>
"""


def get_trace_detail(trace_id):
   
    trace = get_trace_by_id(trace_id)
    return generate_trace_detail_html(trace)