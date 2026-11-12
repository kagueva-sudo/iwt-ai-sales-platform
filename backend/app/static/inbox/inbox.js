(() => {
  const STATUS_LABELS = {
    new: "Новая",
    in_progress: "В работе",
    done: "Готово",
    cancelled: "Отменена",
  };

  const CHANNEL_LABELS = {
    max: "MAX",
    whatsapp: "WhatsApp",
    email: "Email",
    website: "Сайт",
    website_form: "Форма сайта",
    website_chat: "Чат сайта",
    internal: "Внутренний",
  };

  const REASON_LABELS = {
    no_information: "Нет информации",
    no_confirmed_data: "Нет подтверждённых данных",
    price_unknown: "Цена неизвестна",
    availability_unknown: "Наличие неизвестно",
    llm_error: "Ошибка AI",
    timeout: "Таймаут",
    client_request_manager: "Клиент просит менеджера",
    complex_request: "Сложный запрос",
    complex_project: "Сложный проект",
    commercial_offer: "Коммерческое предложение",
    complaint: "Жалоба",
    discount_request: "Запрос скидки",
    email_inbox_review: "Черновик Email",
    unknown: "Не указано",
  };

  const state = {
    items: [],
    filter: "",
    selectedId: null,
  };

  const els = {
    list: document.getElementById("queue-list"),
    listMeta: document.getElementById("list-meta"),
    empty: document.getElementById("empty-state"),
    detail: document.getElementById("detail"),
    detailTitle: document.getElementById("detail-title"),
    detailStatus: document.getElementById("detail-status"),
    detailSub: document.getElementById("detail-sub"),
    metaChannel: document.getElementById("meta-channel"),
    metaContact: document.getElementById("meta-contact"),
    metaReason: document.getElementById("meta-reason"),
    metaCreated: document.getElementById("meta-created"),
    metaId: document.getElementById("meta-id"),
    openChatWrap: document.getElementById("open-chat-wrap"),
    thread: document.getElementById("thread"),
    aiResponse: document.getElementById("ai-response"),
    managerAnswer: document.getElementById("manager-answer"),
    takeBtn: document.getElementById("take-btn"),
    doneBtn: document.getElementById("done-btn"),
    cancelBtn: document.getElementById("cancel-btn"),
    actionHint: document.getElementById("action-hint"),
    refreshBtn: document.getElementById("refresh-btn"),
  };

  function labelStatus(status) {
    return STATUS_LABELS[status] || status;
  }

  function labelChannel(channel) {
    return CHANNEL_LABELS[channel] || channel;
  }

  function labelReason(reason) {
    return REASON_LABELS[reason] || reason;
  }

  function formatDate(value) {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function customerTitle(item) {
    if (item.channel === "email") {
      return (
        item.email_subject ||
        item.customer_name ||
        item.customer_contact ||
        "Письмо без темы"
      );
    }
    return item.customer_name || item.customer_contact || "Без имени";
  }

  function filteredItems() {
    if (!state.filter) return state.items;
    return state.items.filter((item) => item.status === state.filter);
  }

  function selectedItem() {
    return state.items.find((item) => item.request_id === state.selectedId) || null;
  }

  function setHint(text, isError) {
    els.actionHint.textContent = text || "";
    els.actionHint.classList.toggle("error", Boolean(isError));
  }

  function whatsappLink(contact) {
    if (!contact) return null;
    const digits = String(contact).replace(/\D/g, "");
    if (digits.length < 10) return null;
    return `https://wa.me/${digits}`;
  }

  function renderList() {
    const items = filteredItems();
    els.listMeta.textContent =
      items.length === 0
        ? "Заявок нет"
        : `Показано: ${items.length} · всего: ${state.items.length}`;

    els.list.innerHTML = "";
    if (items.length === 0) {
      const empty = document.createElement("div");
      empty.className = "list-meta";
      empty.textContent = "В этом фильтре пусто";
      els.list.appendChild(empty);
      return;
    }

    for (const item of items) {
      const button = document.createElement("button");
      button.type = "button";
      button.className =
        "queue-item" + (item.request_id === state.selectedId ? " active" : "");
      button.setAttribute("role", "listitem");
      button.innerHTML = `
        <div class="queue-item-top">
          <span class="queue-item-title"></span>
          <span class="status-pill status-${item.status}"></span>
        </div>
        <div class="queue-item-meta"></div>
        <div class="queue-item-reason"></div>
      `;
      button.querySelector(".queue-item-title").textContent = customerTitle(item);
      button.querySelector(".status-pill").textContent = labelStatus(item.status);
      button.querySelector(".queue-item-meta").textContent =
        `${labelChannel(item.channel)} · ${formatDate(item.created_at)}`;
      button.querySelector(".queue-item-reason").textContent = labelReason(
        item.handoff_reason
      );
      button.addEventListener("click", () => {
        state.selectedId = item.request_id;
        render();
      });
      els.list.appendChild(button);
    }
  }

  function renderDetail() {
    const item = selectedItem();
    if (!item) {
      els.empty.classList.remove("hidden");
      els.detail.classList.add("hidden");
      return;
    }

    els.empty.classList.add("hidden");
    els.detail.classList.remove("hidden");

    els.detailTitle.textContent = customerTitle(item);
    els.detailStatus.className = `status-pill status-${item.status}`;
    els.detailStatus.textContent = labelStatus(item.status);
    els.detailSub.textContent = `${labelChannel(item.channel)} · ${labelReason(
      item.handoff_reason
    )}`;

    els.metaChannel.textContent = labelChannel(item.channel);
    els.metaContact.textContent = item.customer_contact || "—";
    els.metaReason.textContent = labelReason(item.handoff_reason);
    els.metaCreated.textContent = formatDate(item.created_at);
    els.metaId.textContent = item.request_id;

    els.openChatWrap.innerHTML = "";
    if (item.channel === "whatsapp") {
      const link = whatsappLink(item.customer_contact);
      if (link) {
        const a = document.createElement("a");
        a.className = "btn primary";
        a.href = link;
        a.target = "_blank";
        a.rel = "noopener noreferrer";
        a.textContent = "Открыть чат WhatsApp";
        els.openChatWrap.appendChild(a);
      }
    }

    els.thread.innerHTML = "";
    const history = item.conversation_history || [];
    if (history.length === 0) {
      const empty = document.createElement("p");
      empty.className = "hint";
      empty.textContent = "История переписки пуста";
      els.thread.appendChild(empty);
    } else {
      history.forEach((line, index) => {
        const bubble = document.createElement("div");
        bubble.className = "bubble " + (index % 2 === 0 ? "client" : "other");
        bubble.textContent = line;
        els.thread.appendChild(bubble);
      });
    }

    els.aiResponse.textContent = item.ai_response || "AI ещё не сформировал ответ";

    const closed = item.status === "done" || item.status === "cancelled";
    els.takeBtn.disabled = item.status !== "new";
    els.doneBtn.disabled = closed;
    els.cancelBtn.disabled = closed;
    els.managerAnswer.disabled = closed;

    const answerLabel = document.getElementById("manager-answer-label");
    if (item.channel === "email") {
      if (answerLabel) {
        answerLabel.textContent =
          "Ответ клиенту по Email (уйдёт письмом при «Готово»)";
      }
      els.managerAnswer.placeholder =
        "Отредактируйте черновик AI и нажмите «Готово»";
    } else {
      if (answerLabel) {
        answerLabel.textContent =
          "Ответ менеджера (для обучения, необязательно)";
      }
      els.managerAnswer.placeholder = "Кратко: что ответили клиенту";
    }
    if (!closed && els.managerAnswer.dataset.forId !== item.request_id) {
      els.managerAnswer.value =
        item.channel === "email" ? item.ai_response || "" : "";
      els.managerAnswer.dataset.forId = item.request_id;
    }
  }

  function render() {
    renderList();
    renderDetail();
  }

  async function loadItems() {
    setHint("Обновление…");
    const response = await fetch("/manager-queue");
    if (!response.ok) {
      throw new Error(`Не удалось загрузить очередь (${response.status})`);
    }
    state.items = await response.json();
    if (
      state.selectedId &&
      !state.items.some((item) => item.request_id === state.selectedId)
    ) {
      state.selectedId = null;
    }
    render();
    setHint("");
  }

  async function patchStatus(status) {
    const item = selectedItem();
    if (!item) return;
    setHint("Сохранение…");
    const body = { status };
    if (status === "done") {
      const answer = els.managerAnswer.value.trim();
      if (answer) body.manager_answer = answer;
    }
    const response = await fetch(`/manager-queue/${item.request_id}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `Ошибка ${response.status}`);
    }
    const updated = await response.json();
    state.items = state.items.map((row) =>
      row.request_id === updated.request_id ? updated : row
    );
    render();
    const emailSent =
      status === "done" && item.channel === "email" && (body.manager_answer || "").trim();
    setHint(
      status === "done"
        ? emailSent
          ? "Заявка закрыта, письмо отправлено"
          : "Заявка закрыта"
        : status === "in_progress"
          ? "Заявка взята в работу"
          : "Статус обновлён"
    );
  }

  document.getElementById("filters").addEventListener("click", (event) => {
    const button = event.target.closest(".filter");
    if (!button) return;
    state.filter = button.dataset.status || "";
    document.querySelectorAll(".filter").forEach((el) => {
      el.classList.toggle("active", el === button);
    });
    render();
  });

  els.refreshBtn.addEventListener("click", () => {
    loadItems().catch((error) => setHint(error.message, true));
  });

  els.takeBtn.addEventListener("click", () => {
    patchStatus("in_progress").catch((error) => setHint(error.message, true));
  });

  els.doneBtn.addEventListener("click", () => {
    patchStatus("done").catch((error) => setHint(error.message, true));
  });

  els.cancelBtn.addEventListener("click", () => {
    patchStatus("cancelled").catch((error) => setHint(error.message, true));
  });

  loadItems().catch((error) => {
    els.listMeta.textContent = "Ошибка загрузки";
    setHint(error.message, true);
  });

  setInterval(() => {
    loadItems().catch(() => {});
  }, 30000);
})();
