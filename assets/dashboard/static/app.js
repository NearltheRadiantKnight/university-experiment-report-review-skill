const latestReport = document.getElementById("latestReport");
const reportList = document.getElementById("reportList");
const recordCount = document.getElementById("recordCount");
const refreshButton = document.getElementById("refreshButton");

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function typeBadge(report) {
  const isRevision = report.report_kind === "revision";
  return element("span", `report-type${isRevision ? " revision" : ""}`, isRevision ? "修改报告" : "实验执行报告");
}

function metric(label, value) {
  const row = element("div", "metric");
  row.append(element("span", "", label), element("strong", "", value || "—"));
  return row;
}

function downloadLink(report) {
  const link = element("a", "download-button", "下载 DOCX");
  link.href = report.download_url;
  link.setAttribute("download", report.generated_name);
  return link;
}

function renderLatest(report) {
  latestReport.className = "latest-report";
  latestReport.replaceChildren();
  const grid = element("div", "latest-grid");
  const content = element("div");
  content.append(typeBadge(report));
  content.append(element("div", "latest-title", report.generated_name));
  content.append(element("p", "summary", report.summary || "已基于原始文档生成彩色标注版本。"));
  if (report.verdict) content.append(element("div", "verdict", report.verdict));

  const panel = element("div", "metric-panel");
  panel.append(metric("原始文件", report.source_name));
  panel.append(metric("原始状态", report.source_state));
  panel.append(metric("新增内容", `${report.addition_count || 0} 项`));
  panel.append(metric("生成时间", report.created_at));
  panel.append(downloadLink(report));
  grid.append(content, panel);
  latestReport.append(grid);
}

function renderHistory(reports) {
  reportList.replaceChildren();
  const history = reports.slice(1);
  recordCount.textContent = `${reports.length} 个本地结果`;
  if (!history.length) {
    reportList.append(element("div", "latest-report empty-state", "暂无更多历史记录。"));
    return;
  }
  history.forEach((report) => {
    const card = element("article", "report-card");
    const copy = element("div");
    copy.append(typeBadge(report));
    copy.append(element("h3", "", report.generated_name));
    copy.append(element("p", "", `${report.source_name} · ${report.created_at}`));
    card.append(copy, downloadLink(report));
    reportList.append(card);
  });
}

async function loadReports() {
  refreshButton.disabled = true;
  try {
    const response = await fetch("/api/reports", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    const reports = Array.isArray(payload.reports) ? payload.reports : [];
    if (!reports.length) {
      latestReport.className = "latest-report empty-state";
      latestReport.textContent = "还没有生成文件。请先在 Codex 中上传 DOCX 并运行本 skill。";
      reportList.replaceChildren();
      recordCount.textContent = "0 个本地结果";
      return;
    }
    renderLatest(reports[0]);
    renderHistory(reports);
  } catch (error) {
    latestReport.className = "latest-report empty-state";
    latestReport.textContent = `无法读取本地结果：${error.message}`;
  } finally {
    refreshButton.disabled = false;
  }
}

refreshButton.addEventListener("click", loadReports);
loadReports();
setInterval(loadReports, 5000);
