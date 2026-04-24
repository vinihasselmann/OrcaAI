(() => {
  const form = document.getElementById("upload-form");
  const btn = document.getElementById("submit-btn");
  const resetBtn = document.getElementById("reset-btn");
  const frontError = document.getElementById("frontend-error");
  const resultPanel = document.getElementById("result-panel");
  const resultBanner = document.getElementById("result-banner");
  const resultStatus = document.getElementById("result-status");
  const resultTitle = document.getElementById("result-title");
  const downloadLink = document.getElementById("download-link");
  const resultResetBtn = document.getElementById("result-reset-btn");
  const processLog = document.getElementById("process-log");
  const progressBar = document.getElementById("progress-bar");
  const progressPercent = document.getElementById("progress-percent");
  const selectionSummary = document.getElementById("selection-summary");
  const flowStatus = document.getElementById("flow-status");
  const stepEls = Array.from(document.querySelectorAll(".step"));
  const phaseEls = Array.from(document.querySelectorAll(".phase-pill"));

  if (!form || !btn) return;

  const inputConfig = [
    { id: "arquivo_geral", label: "Geral Pecas (.txt)" },
    { id: "arquivo_auxiliares", label: "Pecas Auxiliares (.txt)" },
    { id: "arquivo_genericas", label: "Pecas Genericas (.txt)" },
    { id: "arquivo_alveolares", label: "Pecas Alveolares (.txt)" },
  ];

  const inputs = inputConfig
    .map((item) => ({
      input: document.getElementById(item.id),
      nameEl: document.getElementById(`${item.id}_nome`),
      infoEl: document.getElementById(`${item.id}_info`),
      label: item.label,
    }))
    .filter((item) => item.input);

  const phases = [
    { key: "leitura", label: "Leitura", progress: 16, log: "Lendo e preparando os arquivos enviados..." },
    { key: "validacao", label: "Validacao", progress: 34, log: "Validando estrutura e campos obrigatorios..." },
    { key: "calculo", label: "Calculo", progress: 56, log: "Aplicando regras de mapeamento e calculo..." },
    { key: "escrita", label: "Escrita", progress: 78, log: "Escrevendo os dados na planilha base..." },
    { key: "exportacao", label: "Exportacao", progress: 92, log: "Preparando a exportacao e o link final..." },
  ];

  let progressTimer = null;
  let currentPhaseIndex = -1;
  let pollTimer = null;

  function formatFileSize(bytes) {
    if (!Number.isFinite(bytes) || bytes <= 0) return "tamanho desconhecido";
    if (bytes < 1024) return `${bytes} b`;
    const kb = bytes / 1024;
    if (kb < 1024) return `${Math.round(kb)} kb`;
    return `${(kb / 1024).toFixed(1)} mb`;
  }

  function setProgress(value) {
    const bounded = Math.max(0, Math.min(100, Math.round(value)));
    if (progressBar) progressBar.style.width = `${bounded}%`;
    if (progressPercent) progressPercent.textContent = `${bounded}%`;
    const track = document.querySelector(".progress-track");
    if (track) track.setAttribute("aria-valuenow", String(bounded));
  }

  function setStepState(activeStep) {
    stepEls.forEach((el, index) => {
      const stepNumber = index + 1;
      el.classList.toggle("is-active", stepNumber === activeStep);
      el.classList.toggle("is-complete", stepNumber < activeStep);
    });
  }

  function phaseIndexFromKey(key) {
    return phases.findIndex((phase) => phase.key === key);
  }

  function setPhaseState(index) {
    phaseEls.forEach((el, phaseIndex) => {
      el.classList.toggle("is-active", phaseIndex === index);
      el.classList.toggle("is-done", phaseIndex < index);
    });
    currentPhaseIndex = index;
  }

  function addLog(message, { muted = false, tone = "" } = {}) {
    if (!processLog) return;
    const line = document.createElement("p");
    const tones = tone ? ` ${tone}` : "";
    line.className = `log-line${muted ? " muted" : tones}`;
    line.textContent = message;
    processLog.appendChild(line);
    processLog.scrollTop = processLog.scrollHeight;
  }

  function clearLog() {
    if (!processLog) return;
    processLog.innerHTML = "";
  }

  function mostrarErro(msg) {
    if (!frontError) return;
    frontError.textContent = msg;
    frontError.classList.remove("hidden");
  }

  function limparErro() {
    if (!frontError) return;
    frontError.textContent = "";
    frontError.classList.add("hidden");
  }

  function updateResult(data) {
    const resumo = data.resumo || {};
    document.getElementById("result-file").textContent = data.nome_arquivo || "-";
    document.getElementById("result-total-arquivos").textContent = resumo.total_arquivos ?? 0;
    document.getElementById("result-total-registros").textContent = resumo.total_registros ?? 0;
    document.getElementById("result-linhas").textContent = resumo.linhas_inseridas ?? 0;
    document.getElementById("result-celulas").textContent = resumo.celulas_escritas ?? 0;
    document.getElementById("result-erros").textContent = resumo.total_erros_escrita ?? 0;
  }

  function showResultSuccess(data) {
    if (!resultPanel || !resultBanner || !resultStatus || !resultTitle || !downloadLink) return;
    resultPanel.classList.remove("hidden");
    resultBanner.classList.remove("is-error");
    resultBanner.classList.add("is-success");
    resultStatus.textContent = "Concluido";
    resultTitle.textContent = "Importacao concluida com sucesso";
    if (data.download_url) {
      downloadLink.href = data.download_url;
      downloadLink.classList.remove("hidden");
    }
    resultResetBtn?.classList.remove("hidden");
    updateResult(data);
  }

  function showResultError(message) {
    if (!resultPanel || !resultBanner || !resultStatus || !resultTitle || !downloadLink) return;
    resultPanel.classList.remove("hidden");
    resultBanner.classList.remove("is-success");
    resultBanner.classList.add("is-error");
    resultStatus.textContent = "Erro";
    resultTitle.textContent = message;
    downloadLink.classList.add("hidden");
    resultResetBtn?.classList.remove("hidden");
  }

  function atualizarNomeArquivo(item) {
    const file = item.input.files && item.input.files[0];
    if (item.nameEl) item.nameEl.textContent = file ? file.name : "Nenhum arquivo selecionado";
    if (item.infoEl) item.infoEl.textContent = file ? `${formatFileSize(file.size)} · carregado` : "Aguardando upload";
    item.input.closest(".file-card")?.classList.toggle("has-file", Boolean(file));
  }

  function resetUI() {
    clearInterval(progressTimer);
    clearInterval(pollTimer);
    progressTimer = null;
    pollTimer = null;
    currentPhaseIndex = -1;
    setProgress(0);
    setStepState(1);
    setPhaseState(-1);
    clearLog();
    addLog("Envie de 1 a 4 arquivos .txt e clique em processar. O arquivo de orcamento sera gerado automaticamente.", { muted: true });
    limparErro();
    if (resultPanel) resultPanel.classList.add("hidden");
    resultResetBtn?.classList.add("hidden");
    downloadLink?.classList.add("hidden");
    if (flowStatus) flowStatus.textContent = "Aguardando arquivos";
    if (selectionSummary) selectionSummary.textContent = `${filesSelecionados().length} de 4 arquivos selecionados`;
    inputs.forEach((item) => item.input.closest(".file-card")?.classList.remove("is-processing"));
    if (btn) {
      btn.disabled = false;
      btn.textContent = "Processar orcamento";
    }
  }

  function startVisualProgress() {
    clearInterval(progressTimer);
    setStepState(2);
    let index = 0;

    const advance = () => {
      if (index >= phases.length) {
        clearInterval(progressTimer);
        return;
      }
      const phase = phases[index];
      setPhaseState(index);
      setProgress(phase.progress);
      addLog(phase.log, { tone: "warn" });
      index += 1;
    };

    advance();
    progressTimer = window.setInterval(advance, 900);
  }

  function filesSelecionados() {
    return inputs.filter((item) => item.input.files && item.input.files.length > 0);
  }

  function registrarArquivosSelecionados() {
    filesSelecionados().forEach((item) => {
      const file = item.input.files[0];
      addLog(`✓ ${file.name} carregado (${formatFileSize(file.size)})`, { tone: "ok" });
    });
  }

  function replaceLogs(logs) {
    if (!processLog) return;
    processLog.innerHTML = "";
    if (!Array.isArray(logs) || !logs.length) {
      addLog("Aguardando retorno do backend...", { muted: true });
      return;
    }
    logs.forEach((entry) => {
      addLog(entry.message || "", { tone: entry.tone || "info" });
    });
  }

  async function pollJob(jobId) {
    clearInterval(progressTimer);
    progressTimer = null;
    clearInterval(pollTimer);

    const tick = async () => {
      const response = await fetch(`/processar-status/${jobId}`, {
        headers: { Accept: "application/json" },
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.erro || "Nao foi possivel consultar o status do processamento.");
      }

      setProgress(data.progress ?? 0);
      setStepState(data.status === "completed" || data.status === "error" ? 3 : 2);

      const phaseIndex = phaseIndexFromKey(data.phase);
      if (phaseIndex >= 0) {
        setPhaseState(
          data.status === "completed" || data.status === "error"
            ? phases.length
            : phaseIndex
        );
      }

      if (flowStatus) {
        if (data.status === "completed") flowStatus.textContent = "Resultado pronto";
        else if (data.status === "error") flowStatus.textContent = "Falha no processamento";
        else flowStatus.textContent = "Processando";
      }

      replaceLogs(data.logs);

      if (data.status === "completed" && data.result) {
        clearInterval(pollTimer);
        pollTimer = null;
        setProgress(100);
        setStepState(3);
        setPhaseState(phases.length);
        showResultSuccess(data.result);
        return;
      }

      if (data.status === "error") {
        clearInterval(pollTimer);
        pollTimer = null;
        setProgress(100);
        setStepState(3);
        setPhaseState(phases.length);
        const errorMessage = data.error || data.message || "Nao foi possivel concluir a importacao.";
        showResultError(errorMessage);
        mostrarErro(errorMessage);
      }
    };

    await tick();
    pollTimer = window.setInterval(() => {
      tick().catch((error) => {
        clearInterval(pollTimer);
        pollTimer = null;
        const errorMessage = error.message || "Falha ao consultar o status do processamento.";
        addLog(errorMessage, { tone: "warn" });
        showResultError(errorMessage);
        mostrarErro(errorMessage);
        inputs.forEach((item) => item.input.closest(".file-card")?.classList.remove("is-processing"));
        btn.disabled = false;
        btn.textContent = "Processar orcamento";
      });
    }, 900);
  }

  function atualizarResumoSelecao() {
    const quantidade = filesSelecionados().length;
    if (selectionSummary) {
      selectionSummary.textContent = `${quantidade} de 4 arquivos selecionados`;
    }
    if (flowStatus) {
      flowStatus.textContent = quantidade ? "Pronto para processar" : "Aguardando arquivos";
    }
  }

  inputs.forEach((item) => {
    item.input.addEventListener("change", () => {
      atualizarNomeArquivo(item);
      atualizarResumoSelecao();
      limparErro();
    });
    atualizarNomeArquivo(item);
  });

  function handleReset() {
    form.reset();
    inputs.forEach(atualizarNomeArquivo);
    atualizarResumoSelecao();
    resetUI();
  }

  resetBtn?.addEventListener("click", handleReset);
  resultResetBtn?.addEventListener("click", handleReset);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    limparErro();

    const selecionados = filesSelecionados();
    if (!selecionados.length) {
      mostrarErro("Selecione ao menos 1 arquivo .txt antes de processar.");
      return;
    }

    if (btn.disabled) return;

    btn.disabled = true;
    btn.textContent = "Processando orcamento...";
    if (resultPanel) resultPanel.classList.add("hidden");
    resultResetBtn?.classList.add("hidden");
    clearLog();
    registrarArquivosSelecionados();
    if (flowStatus) flowStatus.textContent = "Processando";
    selecionados.forEach((item) => item.input.closest(".file-card")?.classList.add("is-processing"));
    startVisualProgress();

    try {
      const formData = new FormData(form);
      const response = await fetch("/processar-async", {
        method: "POST",
        body: formData,
        headers: {
          Accept: "application/json",
          "X-Requested-With": "fetch",
        },
      });

      const data = await response.json();

      clearInterval(progressTimer);
      progressTimer = null;

      if (!response.ok || !data.job_id) {
        const errorMessage = data.erro || "Nao foi possivel iniciar a importacao.";
        setProgress(100);
        setStepState(3);
        setPhaseState(phases.length);
        if (flowStatus) flowStatus.textContent = "Falha no processamento";
        addLog(errorMessage, { tone: "warn" });
        showResultError(errorMessage);
        mostrarErro(errorMessage);
        return;
      }
      addLog("Job criado. Acompanhando progresso real do backend...", { tone: "info" });
      await pollJob(data.job_id);
    } catch (error) {
      clearInterval(progressTimer);
      progressTimer = null;
      clearInterval(pollTimer);
      pollTimer = null;
      setProgress(100);
      setStepState(3);
      const errorMessage = "Falha de comunicacao com o servidor. Tente novamente.";
      if (flowStatus) flowStatus.textContent = "Falha de comunicacao";
      addLog(errorMessage, { tone: "warn" });
      showResultError(errorMessage);
      mostrarErro(errorMessage);
    } finally {
      inputs.forEach((item) => item.input.closest(".file-card")?.classList.remove("is-processing"));
      btn.disabled = false;
      btn.textContent = "Processar orcamento";
    }
  });

  atualizarResumoSelecao();
})();
