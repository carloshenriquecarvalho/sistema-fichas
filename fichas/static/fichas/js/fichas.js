"use strict";

// Dialogs nativos: mantêm foco, fecham com Esc e aceitam os botões Cancelar/×.
document.querySelectorAll("[data-open]").forEach((botao) => {
    botao.addEventListener("click", () => {
        const modal = document.getElementById(botao.dataset.open);
        if (modal && !modal.open) modal.showModal();
    });
});
document.querySelectorAll("[data-close]").forEach((botao) => {
    botao.addEventListener("click", () => botao.closest("dialog")?.close());
});
document.querySelectorAll("dialog[data-autoopen]").forEach((modal) => {
    if (!modal.open) modal.showModal();
});

// O backend aplica a mesma regra: esconder no navegador, sozinho, não valida nada.
document.querySelectorAll("[data-form-ficha]").forEach((container) => {
    const checkbox = container.querySelector('[name="usar_cnpj"]');
    if (!checkbox) return;
    function atualizarCnpj() {
        container.querySelectorAll("[data-cnpj]").forEach((grupo) => {
            grupo.hidden = !checkbox.checked;
            const campo = grupo.querySelector("input, select, textarea");
            if (!campo) return;
            campo.disabled = !checkbox.checked;
            campo.required = checkbox.checked;
        });
    }
    checkbox.addEventListener("change", atualizarCnpj);
    atualizarCnpj();
});

const quadro = document.querySelector("[data-quadro]");
if (quadro) {
    let cartaoArrastado = null;
    let salvando = false;
    const status = document.getElementById("status-quadro");
    const anunciar = (mensagem, erro = false) => {
        status.textContent = mensagem;
        status.hidden = false;
        status.classList.toggle("status--erro", erro);
    };

    async function mover(cartao, destino) {
        if (salvando || destino === cartao.dataset.etapaOrigem) return;
        const token = cartao.querySelector('[name="csrfmiddlewaretoken"]')?.value;
        if (!token) return;
        salvando = true;
        cartao.setAttribute("aria-busy", "true");
        anunciar("Salvando nova etapa…");
        try {
            const resposta = await fetch(cartao.dataset.moverUrl, {
                method: "POST", mode: "same-origin", credentials: "same-origin",
                headers: {"X-CSRFToken": token, "Accept": "application/json"},
                body: new URLSearchParams({etapa: destino, etapa_origem: cartao.dataset.etapaOrigem}),
            });
            if (resposta.redirected) throw new Error("Sua sessão pode ter expirado. Atualize a página e entre novamente.");
            const tipo = resposta.headers.get("content-type") || "";
            const dados = tipo.includes("application/json") ? await resposta.json() : null;
            if (!resposta.ok || !dados?.ok) {
                throw new Error(dados?.erro || "Não foi possível mover a ficha. Confira sua sessão e suas permissões.");
            }
            // Só atualiza a tela depois da confirmação do servidor.
            window.location.reload();
        } catch (erro) {
            anunciar(erro.message || "Falha de conexão. Tente novamente.", true);
            salvando = false;
            cartao.removeAttribute("aria-busy");
        }
    }

    quadro.querySelectorAll('.cartao[draggable="true"]').forEach((cartao) => {
        cartao.addEventListener("dragstart", (evento) => {
            if (salvando || evento.target.closest("a, button, input, select")) {
                evento.preventDefault(); return;
            }
            cartaoArrastado = cartao;
            evento.dataTransfer.effectAllowed = "move";
            evento.dataTransfer.setData("text/plain", cartao.dataset.fichaId);
            cartao.classList.add("arrastando");
        });
        cartao.addEventListener("dragend", () => {
            cartao.classList.remove("arrastando");
            quadro.querySelectorAll(".coluna").forEach((coluna) => coluna.classList.remove("recebendo"));
            cartaoArrastado = null;
        });
    });
    quadro.querySelectorAll("[data-etapa-id]").forEach((coluna) => {
        coluna.addEventListener("dragover", (evento) => {
            if (!cartaoArrastado || salvando) return;
            evento.preventDefault();
            evento.dataTransfer.dropEffect = "move";
            coluna.classList.add("recebendo");
        });
        coluna.addEventListener("dragleave", (evento) => {
            if (!coluna.contains(evento.relatedTarget)) coluna.classList.remove("recebendo");
        });
        coluna.addEventListener("drop", (evento) => {
            evento.preventDefault();
            coluna.classList.remove("recebendo");
            if (cartaoArrastado) mover(cartaoArrastado, coluna.dataset.etapaId);
        });
    });
    // O select/botão funciona com mouse, teclado e toque. Sem JS, usa POST normal.
    quadro.querySelectorAll(".mover-form").forEach((formulario) => {
        formulario.addEventListener("submit", (evento) => {
            evento.preventDefault();
            mover(formulario.closest(".cartao"), formulario.elements.etapa.value);
        });
    });
}
