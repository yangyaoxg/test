const state = {
  student: null,
  currentPaper: null,
  lastWeakPoints: [],
};

const $ = (id) => document.getElementById(id);

async function api(path, payload, method = "POST") {
  const options = { method, headers: { "Content-Type": "application/json" } };
  if (payload) options.body = JSON.stringify(payload);
  const res = await fetch(path, options);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `请求失败: ${res.status}`);
  }
  return await res.json();
}

function renderPaper(container, paper) {
  container.innerHTML = "";
  if (!paper || !paper.questions?.length) {
    container.innerHTML = "<p class='tip'>暂无题目</p>";
    return;
  }

  paper.questions.forEach((q) => {
    const div = document.createElement("div");
    div.className = "paper-item";
    const optionsHtml = q.options
      .map((opt) => {
        const key = opt[0];
        return `<label class="option-label"><input type="radio" name="q_${q.idx}" value="${key}"/>${opt}</label>`;
      })
      .join("");

    div.innerHTML = `
      <strong>第${q.idx}题：</strong>${q.stem}
      <div class="tip">知识点：${q.knowledge_point}</div>
      <div class="options">${optionsHtml}</div>
    `;
    container.appendChild(div);
  });
}

function collectAnswers(container) {
  const answers = {};
  if (!state.currentPaper) return answers;
  state.currentPaper.questions.forEach((q) => {
    const checked = container.querySelector(`input[name="q_${q.idx}"]:checked`);
    answers[String(q.idx)] = checked ? checked.value : "";
  });
  return answers;
}

function renderDashboard(dashboard) {
  const wrap = $("dashboardWrap");
  const progress = dashboard.progress || [];
  if (!progress.length) {
    wrap.innerHTML = "<p class='tip'>还没有学习记录，快去闯关吧！</p>";
    return;
  }

  wrap.innerHTML = `<div class="kpi">${progress
    .map(
      (item) => `
      <div class="kpi-card">
        <strong>${item.knowledge_point}</strong>
        <div>正确率：${item.accuracy}%（${item.correct_count}/${item.total_count}）</div>
        <div class="progress-bar"><div class="progress-fill" style="width:${item.accuracy}%"></div></div>
      </div>
    `
    )
    .join("")}</div>`;
}

function initEvents() {
  $("createStudentBtn").addEventListener("click", async () => {
    const name = $("studentName").value.trim();
    if (!name) {
      alert("请先输入姓名哦～");
      return;
    }

    try {
      const res = await api("/api/student/create", { name, grade: "四年级下" });
      state.student = res.student;
      $("studentInfo").textContent = `已创建：${state.student.name}（ID: ${state.student.id}）`;
      $("generatePaperBtn").disabled = false;
      $("refreshDashboardBtn").disabled = false;
    } catch (err) {
      alert(`创建失败：${err.message}`);
    }
  });

  $("generatePaperBtn").addEventListener("click", async () => {
    if (!state.student) return alert("请先创建学生档案");
    try {
      const res = await api("/api/paper/generate", { student_id: state.student.id, count: 20 });
      state.currentPaper = res.paper;
      renderPaper($("paperWrap"), state.currentPaper);
      $("submitPaperBtn").disabled = false;
    } catch (err) {
      alert(`生成试卷失败：${err.message}`);
    }
  });

  $("submitPaperBtn").addEventListener("click", async () => {
    if (!state.student || !state.currentPaper) return;
    const answers = collectAnswers($("paperWrap"));

    try {
      const res = await api("/api/paper/submit", {
        student_id: state.student.id,
        paper_id: state.currentPaper.paper_id,
        answers,
      });
      const analysis = res.analysis;
      state.lastWeakPoints = analysis.weak_points || [];
      alert(
        `本次得分 ${analysis.score} 分！\n答对 ${analysis.correct}/${analysis.total} 题。\n薄弱点：${
          state.lastWeakPoints.length ? state.lastWeakPoints.join("、") : "太棒了，暂未发现明显薄弱点"
        }`
      );
      $("generateReinforceBtn").disabled = state.lastWeakPoints.length === 0;
    } catch (err) {
      alert(`交卷失败：${err.message}`);
    }
  });

  $("refreshDashboardBtn").addEventListener("click", async () => {
    if (!state.student) return;
    try {
      const res = await api(`/api/student/${state.student.id}/dashboard`, null, "GET");
      renderDashboard(res.dashboard);
    } catch (err) {
      alert(`加载档案失败：${err.message}`);
    }
  });

  $("generateReinforceBtn").addEventListener("click", async () => {
    if (!state.student || !state.lastWeakPoints.length) return;
    try {
      const res = await api("/api/paper/reinforce", {
        student_id: state.student.id,
        weak_points: state.lastWeakPoints,
        count: 10,
      });
      renderPaper($("reinforceWrap"), res.paper);
    } catch (err) {
      alert(`生成强化卷失败：${err.message}`);
    }
  });
}

initEvents();
