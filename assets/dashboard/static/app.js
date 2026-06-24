const latestReport=document.getElementById("latestReport"),reportList=document.getElementById("reportList"),recordCount=document.getElementById("recordCount"),refreshButton=document.getElementById("refreshButton");
function element(tag,className,text){const node=document.createElement(tag);if(className)node.className=className;if(text!==undefined)node.textContent=text;return node;}
async function readJson(response){const contentType=response.headers.get("content-type")||"";if(!response.ok)throw new Error(`HTTP ${response.status}`);if(!contentType.includes("application/json"))throw new Error("\u672c\u5730\u670d\u52a1\u7248\u672c\u4e0d\u5339\u914d\uff0c\u8bf7\u5173\u95ed\u65e7\u9875\u9762\u5e76\u4f7f\u7528\u672c\u6b21\u751f\u6210\u7684\u65b0\u5730\u5740");return response.json();}
function typeBadge(report){const revision=report.report_kind==="revision";return element("span",`report-type${revision?" revision":""}`,revision?"修改报告":"实验执行报告");}
function metric(label,value){const row=element("div","metric");row.append(element("span","",label),element("strong","",value||"—"));return row;}
function reportFiles(report){const files=Array.isArray(report.files)?[...report.files]:[];if(!files.length&&report.download_url)files.push({kind:"annotated",label:report.report_label||"\u4e0b\u8f7d\u62a5\u544a",name:report.generated_name||"report.docx",download_url:report.download_url});return files;}
function fileLinks(report,compact=false){const wrap=element("div",compact?"file-actions compact":"file-actions");reportFiles(report).filter(file=>file.kind!=="render-preview"&&file.kind!=="companion"&&file.kind!=="quality"&&file.kind!=="rendered-pdf").forEach(file=>{const link=element("a",`download-button ${file.kind||""}`,file.label||"\u4e0b\u8f7d");link.href=file.download_url;link.setAttribute("download",file.name);wrap.append(link);});return wrap;}
function prioritySummary(report){const counts=report.priority_counts||{},wrap=element("div","priority-row");[["blocker","阻塞"],["high","高"],["medium","中"],["low","低"],["optional","可选"]].forEach(([key,label])=>{if(counts[key])wrap.append(element("span",`priority ${key}`,`${label} ${counts[key]}`));});return wrap;}
function renderCompanionContent(report){
 const actions=report.actions;if(!Array.isArray(actions)||!actions.length)return null;
 const section=element("section","companion-content"),title=report.report_kind==="revision"?"报告修改清单":"实验执行清单";
 section.append(element("h3","companion-title",title));
 if(report.verdict)section.append(element("div","companion-verdict","提交判断："+report.verdict));
 if(report.summary)section.append(element("div","companion-summary","整体说明："+report.summary));
 const table=element("table","companion-table"),thead=document.createElement("thead"),headerRow=document.createElement("tr");
 ["优先级","类别","依据","行动"].forEach(text=>{const th=document.createElement("th");th.textContent=text;headerRow.append(th);});
 thead.append(headerRow);table.append(thead);
 const tbody=document.createElement("tbody");
 actions.forEach(action=>{
  const row=document.createElement("tr");row.className="companion-priority-"+action.priority;
  const priorityCell=document.createElement("td");priorityCell.textContent=action.priority_label||action.priority||"中";
  const categoryCell=document.createElement("td");categoryCell.textContent=action.label||"";
  const evidenceCell=document.createElement("td");evidenceCell.textContent=action.evidence_basis||"";
  const textCell=document.createElement("td");textCell.textContent=action.text||"";
  row.append(priorityCell,categoryCell,evidenceCell,textCell);tbody.append(row);
 });
 table.append(tbody);section.append(table);return section;
}
function feedbackRow(action){const row=element("div","feedback-row");row.dataset.actionId=action.action_id;const _m={blocker:"blocker",high:"high",medium:"medium",low:"low",optional:"optional",阻塞:"blocker",高:"high",中:"medium",低:"low",可选:"optional"};const pri=_m[action.priority]||_m[action.priority_label]||action.priority||"medium";const disp={blocker:"阻塞",high:"高",medium:"中",low:"低",optional:"可选"}[pri]||action.priority_label||"中";row.dataset.priority=pri;const head=element("div","feedback-head");head.append(element("span",`priority ${pri}`,disp),element("strong","",action.label||`行动 ${action.action_id}`));const correction=element("textarea","feedback-correction");correction.placeholder="补充事实、修正判断或说明无法完成的原因";correction.value=action.correction||action.note||"";row.append(head,correction);return row;}
function legacyFeedback(report){
 const key=`experiment-report-feedback:${report.job_id}`;
 try{const saved=JSON.parse(localStorage.getItem(key)||"null");if(saved&&Array.isArray(saved.actions)){
  const srcActions=Array.isArray(report.actions)?report.actions:[];
  saved.actions.forEach((a,i)=>{if(i<srcActions.length)a.priority=srcActions[i].priority||srcActions[i].priority_label||a.priority||"medium";});
  return saved;
 }}catch(error){}
 const sourceActions=Array.isArray(report.actions)?report.actions:[];
 const actions=sourceActions.map((action,index)=>({action_id:index+1,label:action.label||`\u884c\u52a8 ${index+1}`,priority:action.priority||"medium",priority_label:action.priority_label||"",status:"open",note:"",correction:""}));
 if(!actions.length)actions.push({action_id:1,label:"\u8865\u5145\u786e\u8ba4\u4fe1\u606f",priority:"medium",status:"open",note:"",correction:""});
 return {job_id:report.job_id,source_name:report.source_name,updated_at:null,confirmed_context:{},actions};
}
function collectFeedback(report,rows,context){return {job_id:report.job_id,source_name:report.source_name,updated_at:new Date().toISOString(),confirmed_context:{user_notes:context.value},actions:[...rows.querySelectorAll(".feedback-row")].map(row=>({action_id:Number(row.dataset.actionId),label:row.querySelector("strong").textContent,priority:row.dataset.priority||"medium",priority_label:row.querySelector(".priority").textContent,status:"open",correction:row.querySelector("textarea").value,note:""}))};}
function downloadFeedback(payload){const blob=new Blob([JSON.stringify(payload,null,2)],{type:"application/json;charset=utf-8"}),url=URL.createObjectURL(blob),link=document.createElement("a");link.href=url;link.download=`${payload.job_id}.feedback.json`;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
async function renderFeedback(report,container){
 const section=element("section","feedback-panel"),heading=element("div","feedback-title");heading.append(element("div","","") ,element("h3","","\u672c\u5730\u53cd\u9988\u95ed\u73af"));section.append(heading,element("p","feedback-help","\u586b\u5199\u8865\u5145\u4fe1\u606f\u5e76\u4fdd\u5b58\u3002\u65b0\u670d\u52a1\u4f1a\u4fdd\u5b58\u5230\u8f93\u51fa\u76ee\u5f55\uff1b\u65e7\u670d\u52a1\u4f1a\u76f4\u63a5\u4e0b\u8f7d feedback JSON\u3002"));
 const rows=element("div","feedback-rows"),context=element("textarea","feedback-context");context.placeholder="\u8865\u5145\u5b9e\u9a8c\u73af\u5883\u3001\u6559\u5e08\u8981\u6c42\u3001\u8d26\u53f7\u5f52\u5c5e\u6216\u5176\u4ed6\u5df2\u786e\u8ba4\u4fe1\u606f";section.append(rows,context);
 const actions=element("div","feedback-actions"),save=element("button","save-feedback","\u4fdd\u5b58\u53cd\u9988"),status=element("span","feedback-message","");actions.append(save,status);section.append(actions);container.append(section);
 let compatibilityMode=false,feedback;
 try{const response=await fetch(`/api/reports/${report.job_id}/feedback`,{cache:"no-store"});if(response.status===404){compatibilityMode=true;feedback=legacyFeedback(report);}else feedback=await readJson(response);}catch(error){compatibilityMode=true;feedback=legacyFeedback(report);}
 (feedback.actions||[]).forEach(action=>rows.append(feedbackRow(action)));context.value=feedback.confirmed_context?.user_notes||"";
 if(compatibilityMode)status.textContent="\u517c\u5bb9\u6a21\u5f0f\uff1a\u70b9\u51fb\u4fdd\u5b58\u540e\u76f4\u63a5\u4e0b\u8f7d JSON\u3002";
 save.addEventListener("click",async()=>{save.disabled=true;const payload=collectFeedback(report,rows,context);localStorage.setItem(`experiment-report-feedback:${report.job_id}`,JSON.stringify(payload));try{if(compatibilityMode){downloadFeedback(payload);status.textContent="\u5df2\u4fdd\u5b58\u5e76\u4e0b\u8f7d feedback JSON\u3002";return;}const response=await fetch(`/api/reports/${report.job_id}/feedback`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});if(response.status===404){compatibilityMode=true;downloadFeedback(payload);status.textContent="\u65e7\u670d\u52a1\u517c\u5bb9\u4fdd\u5b58\uff1a\u5df2\u4e0b\u8f7d feedback JSON\u3002";return;}const result=await readJson(response);status.replaceChildren(element("span","","\u5df2\u4fdd\u5b58\u3002"));const link=element("a","feedback-download","\u4e0b\u8f7d\u53cd\u9988 JSON");link.href=result.download_url;status.append(link);}catch(error){downloadFeedback(payload);status.textContent="\u670d\u52a1\u4fdd\u5b58\u4e0d\u53ef\u7528\uff0c\u5df2\u6539\u4e3a\u672c\u5730\u4e0b\u8f7d JSON\u3002";}finally{save.disabled=false;}});
}
function renderLatest(report){latestReport.className="latest-report";latestReport.replaceChildren();const grid=element("div","latest-grid"),content=element("div");content.append(typeBadge(report),element("div","latest-title",report.generated_name),element("p","summary",report.summary||"已生成本地报告。"));if(report.verdict)content.append(element("div","verdict",report.verdict));content.append(prioritySummary(report));const panel=element("div","metric-panel");panel.append(metric("原始文件",report.source_name),metric("原始状态",report.source_state),metric("领域",report.domain_profile||"通用"),metric("新增内容",`${report.addition_count||0} 项`),metric("生成时间",report.created_at),fileLinks(report));grid.append(content,panel);latestReport.append(grid);const companion=renderCompanionContent(report);if(companion)latestReport.append(companion);renderFeedback(report,latestReport);}
function renderHistory(reports){reportList.replaceChildren();recordCount.textContent=`${reports.length} \u4e2a\u672c\u5730\u7ed3\u679c`;reports.forEach((report,index)=>{const card=element("article","report-card"),copy=element("div");copy.append(typeBadge(report),element("h3","",report.generated_name),element("p","",`${report.source_name} \u00b7 ${report.created_at}${index===0?" \u00b7 \u6700\u65b0":""}`));card.append(copy,fileLinks(report,true));reportList.append(card);});}
async function loadReports(){refreshButton.disabled=true;try{const response=await fetch("/api/reports",{cache:"no-store"});const reports=(await readJson(response)).reports||[];if(!reports.length){latestReport.className="latest-report empty-state";latestReport.textContent="还没有生成文件。请先在支持 AgentSkills 的客户端运行本 skill。";reportList.replaceChildren();recordCount.textContent="0 个本地结果";return;}renderLatest(reports[0]);renderHistory(reports);}catch(error){latestReport.className="latest-report empty-state";latestReport.textContent=`无法读取本地结果：${error.message}`;}finally{refreshButton.disabled=false;}}
refreshButton.addEventListener("click",loadReports);
//loadReports();setInterval(loadReports,8000);

/* ── 历史反馈弹窗 ── */
const FEEDBACK_NS="experiment-report-feedback:";
function isLocalFeedbackKey(key){return key.startsWith(FEEDBACK_NS);}
function jobIdFromKey(key){return key.slice(FEEDBACK_NS.length);}

async function loadAllFeedback(){
 const locals=[];
 for(let i=0;i<localStorage.length;i++){
  const key=localStorage.key(i);
  if(!isLocalFeedbackKey(key))continue;
  try{const data=JSON.parse(localStorage.getItem(key));if(data&&Array.isArray(data.actions))locals.push(data);}catch(e){}
 }
 let remotes=[];
 try{const resp=await fetch("/api/feedback",{cache:"no-store"});const body=await readJson(resp);remotes=body.feedback||[];}catch(e){}
 const seen=new Set();
 const merged=[];
 remotes.forEach(f=>{seen.add(f.job_id);merged.push(f);});
 locals.forEach(f=>{if(!seen.has(f.job_id))merged.push(f);});
 merged.sort((a,b)=>(b.updated_at||"").localeCompare(a.updated_at||""));
 return merged;
}

function openHistoryModal(){
 let overlay=document.getElementById("historyFeedbackOverlay");
 if(overlay){overlay.style.display="flex";return;}
 overlay=element("div","modal-overlay");overlay.id="historyFeedbackOverlay";
 const modal=element("div","modal-content");
 const header=element("div","modal-header");
 header.append(element("h2","","历史反馈"));
 const closeBtn=element("button","modal-close","×");
 closeBtn.addEventListener("click",()=>overlay.style.display="none");
 header.append(closeBtn);
 modal.append(header);
 const body=element("div","modal-body");body.id="historyFeedbackBody";
 body.innerHTML='<p style="color:var(--muted);text-align:center;padding:40px 0;">正在加载…</p>';
 modal.append(body);
 const footer=element("div","modal-footer");
 footer.textContent="点击卡片展开查看详情 · 可在输入框中修改反馈内容 · 点击×删除单条行动";
 modal.append(footer);
 overlay.append(modal);
 overlay.addEventListener("click",e=>{if(e.target===overlay)overlay.style.display="none";});
 document.body.append(overlay);
 loadAllFeedback().then(feedbacks=>renderHistoryFeedbackList(body,feedbacks)).catch(()=>{body.innerHTML='<p style="color:var(--muted);text-align:center;padding:40px 0;">加载失败。</p>';});
}

function renderHistoryFeedbackList(container,feedbacks){
 if(!feedbacks.length){container.innerHTML='<p style="color:var(--muted);text-align:center;padding:40px 0;">暂无历史反馈。</p>';return;}
 const list=element("div","feedback-history-list");
 feedbacks.forEach(fb=>{
  const item=element("div","feedback-history-item");
  const head=element("div","feedback-history-head");
  const meta=element("div","feedback-history-meta");
  const actionsCount=Array.isArray(fb.actions)?fb.actions.length:0;
  const doneCount=fb.actions?fb.actions.filter(a=>a.status==="done"||a.correction).length:0;
  meta.innerHTML=`<strong>${fb.source_name||"未知来源"}</strong> · `+
   `<span class="meta-muted">${fb.job_id||""}</span><br>`+
   `<span class="meta-muted">${fb.updated_at?"更新 "+fb.updated_at:"未保存"}`+
   ` · ${doneCount}/${actionsCount} 条已处理</span>`;
  const arrow=element("span","feedback-history-arrow","▼");
  head.append(meta,arrow);
  item.append(head);
  const body=element("div","feedback-history-body");
  const notes=element("textarea","feedback-history-notes");
  notes.placeholder="补充实验环境、教师要求、账号归属或其他已确认信息";
  notes.value=fb.confirmed_context?.user_notes||"";
  if(!fb.confirmed_context)fb.confirmed_context={};
  notes.addEventListener("input",()=>{fb.confirmed_context.user_notes=notes.value;});
  body.append(notes);
  renderHistoryFeedbackActions(body,fb);
  item.append(body);
  head.addEventListener("click",()=>item.classList.toggle("expanded"));
  list.append(item);
 });
 container.replaceChildren(list);
}

function renderHistoryFeedbackActions(container,feedback){
 container.replaceChildren();
 const apiAvailable=feedback.updated_at!==null&&feedback.updated_at!=="";
 if(!Array.isArray(feedback.actions)||!feedback.actions.length){
  container.innerHTML='<p style="color:var(--muted);font-size:13px;padding:10px 0;">暂无行动项。</p>';
  return;
 }
 function onDataChanged(){
  localStorage.setItem(`${FEEDBACK_NS}${feedback.job_id}`,JSON.stringify(feedback));
 }
 feedback.actions.forEach((action,idx)=>{
  const row=element("div","history-action-row");
  const label=element("div","history-action-label",action.label||`行动 ${action.action_id}`);
  const inputGroup=element("div","history-action-input-group");
  const input=element("textarea","history-action-input");
  input.placeholder="补充事实、修正判断或说明无法完成的原因";
  input.value=action.correction||action.note||"";
  input.addEventListener("input",()=>{action.correction=input.value;onDataChanged();});
  const delBtn=element("button","delete-action-btn","✕");
  delBtn.title="删除此条行动";
  delBtn.addEventListener("click",async()=>{
   feedback.actions.splice(idx,1);
   if(apiAvailable){
    try{
     const resp=await fetch(`/api/reports/${feedback.job_id}/feedback`,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({confirmed_context:feedback.confirmed_context||{},actions:feedback.actions})});
     if(!resp.ok)throw new Error();
    }catch(e){feedback.actions.splice(idx,0,action);return;}
   }
   renderHistoryFeedbackActions(container,feedback);
  });
  inputGroup.append(input,delBtn);
  row.append(label,inputGroup);
  container.append(row);
 });
 const saveRow=element("div","feedback-save-row");
 const saveBtn=element("button","save-feedback","保存修改");
 const msg=element("span","feedback-message","");
 saveBtn.addEventListener("click",async()=>{
  saveBtn.disabled=true;
  feedback.updated_at=new Date().toISOString();
  onDataChanged();
  if(apiAvailable){
   try{
    const resp=await fetch(`/api/reports/${feedback.job_id}/feedback`,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({confirmed_context:feedback.confirmed_context||{},actions:feedback.actions})});
    if(!resp.ok)throw new Error();
    msg.textContent="已保存到服务端。";
   }catch(e){downloadFeedback(feedback);msg.textContent="服务不可用，已下载 JSON。";}
  }else{downloadFeedback(feedback);msg.textContent="已下载 JSON。";}
  saveBtn.disabled=false;
 });
 saveRow.append(saveBtn,msg);
 container.append(saveRow);
}

document.addEventListener("DOMContentLoaded",()=>{
 const btn=document.getElementById("historyFeedbackBtn");
 if(btn)btn.addEventListener("click",openHistoryModal);
});
