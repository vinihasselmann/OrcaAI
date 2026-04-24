(() => {
  const form = document.getElementById("upload-form");
  const btn = document.getElementById("submit-btn");
  const frontError = document.getElementById("frontend-error");
  if (!form || !btn) return;

  const inputs = [
    document.getElementById("arquivo_geral"),
    document.getElementById("arquivo_auxiliares"),
    document.getElementById("arquivo_genericas"),
    document.getElementById("arquivo_alveolares"),
  ].filter(Boolean);

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

  function atualizarNomeArquivo(input) {
    const label = document.getElementById(`${input.id}_nome`);
    if (!label) return;
    const file = input.files && input.files[0];
    label.textContent = file ? file.name : "Nenhum arquivo selecionado.";
  }

  inputs.forEach((input) => {
    input.addEventListener("change", () => {
      atualizarNomeArquivo(input);
      limparErro();
    });
  });

  form.addEventListener("submit", (event) => {
    const possuiArquivo = inputs.some((input) => input.files && input.files.length > 0);
    if (!possuiArquivo) {
      event.preventDefault();
      mostrarErro("Selecione ao menos 1 arquivo .txt antes de processar.");
      return;
    }

    if (btn.disabled) {
      event.preventDefault();
      return;
    }

    btn.disabled = true;
    btn.textContent = "Processando...";
  });
})();
