# Плавающая кнопка мессенджеров IWT — ТЗ и код для Bitrix

**Кому:** администратор сайта iwt.ru (Bitrix)  
**Задача:** добавить одну плавающую кнопку «Задать вопрос» с выбором WhatsApp (AI-бот) и MAX (бот).  
**Срок установки:** ~15–30 минут.

---

## 1. Цель

Клиент на сайте нажимает кнопку → выбирает мессенджер → сразу открывается чат с ботом IWT.

| Канал | Куда ведёт | Ссылка |
|--------|------------|--------|
| WhatsApp | AI-бот Cloud API | `https://wa.me/79285550048?text=%D0%9F%D1%80%D0%B8%D0%B2%D0%B5%D1%82%20%D1%81%20%D1%81%D0%B0%D0%B9%D1%82%D0%B0%20iwt.ru` |
| MAX | Бот «ООО ИВТ» | `https://max.ru/id0541026800_bot?start=site` |

**Важно:** на WhatsApp ведём на бота `+7 928 555-00-48`, **не** на бизнес-аккаунт `+7 903 488-00-77`.

---

## 2. Требования к UX

1. Одна круглая кнопка справа внизу.
2. По клику — меню из двух пунктов: WhatsApp и MAX.
3. Повторный клик по кнопке или клик вне меню — закрыть меню.
4. Меню **не** открывать автоматически.
5. Без агрессивной анимации / пульсации.
6. На мобильных не перекрывать нижнюю навигацию Bitrix / корзину (отступ снизу увеличен).
7. Ссылки открывать в новой вкладке: `target="_blank"` + `rel="noopener noreferrer"`.
8. Если на сайте уже есть Jivo / Битрикс24 Online Chat — согласовать позицию (не накладывать друг на друга).

---

## 3. Куда вставить в Bitrix

Рекомендуемый способ:

1. Админка Bitrix → **Настройки** → **Настройки продукта** → **Сайты** → **Шаблоны сайта**.
2. Активный шаблон сайта → файл **`footer.php`**.
3. Вставить код из раздела 4 **перед** закрывающим тегом `</body>` (или в самом конце подвала, чтобы блок был на всех страницах).

Альтернатива: включаемая область в подвале / общее свойство шаблона — главное, чтобы код был на всех публичных страницах.

После вставки: сбросить кеш Bitrix (и CDN/композит, если включены).

---

## 4. Готовый код (вставить как есть)

```html
<!-- ========== IWT messenger float: WhatsApp bot + MAX ========== -->
<style>
  .iwt-msg {
    --iwt-accent: #0f5c4c;
    --iwt-wa: #25d366;
    --iwt-max: #1a73e8;
    position: fixed;
    right: 18px;
    bottom: calc(18px + env(safe-area-inset-bottom, 0px));
    z-index: 9990;
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  }
  @media (max-width: 768px) {
    .iwt-msg {
      right: 14px;
      bottom: calc(72px + env(safe-area-inset-bottom, 0px));
    }
  }
  .iwt-msg__btn {
    width: 56px;
    height: 56px;
    border-radius: 50%;
    border: 0;
    cursor: pointer;
    background: var(--iwt-accent);
    color: #fff;
    box-shadow: 0 8px 24px rgba(15, 92, 76, 0.35);
    display: grid;
    place-items: center;
    transition: transform 0.15s ease, background 0.15s ease;
  }
  .iwt-msg__btn:hover {
    transform: scale(1.05);
    background: #0a463a;
  }
  .iwt-msg__btn svg {
    width: 26px;
    height: 26px;
    display: block;
  }
  .iwt-msg__panel {
    position: absolute;
    right: 0;
    bottom: 68px;
    width: min(260px, calc(100vw - 32px));
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.14);
    padding: 10px;
    display: none;
  }
  .iwt-msg.is-open .iwt-msg__panel {
    display: block;
  }
  .iwt-msg__title {
    font-size: 13px;
    color: #5b6470;
    margin: 2px 8px 8px;
    font-weight: 600;
  }
  .iwt-msg__link {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    border-radius: 10px;
    text-decoration: none;
    color: #1c2420;
    font-size: 15px;
    font-weight: 600;
  }
  .iwt-msg__link:hover {
    background: #f3f4f6;
  }
  .iwt-msg__ico {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    display: grid;
    place-items: center;
    color: #fff;
    flex: 0 0 auto;
  }
  .iwt-msg__ico--wa { background: var(--iwt-wa); }
  .iwt-msg__ico--max { background: var(--iwt-max); }
  .iwt-msg__hint {
    display: block;
    font-size: 12px;
    font-weight: 500;
    color: #6b7280;
    margin-top: 2px;
  }
</style>

<div class="iwt-msg" id="iwt-msg">
  <div class="iwt-msg__panel" id="iwt-msg-panel" role="menu" aria-label="Выбор мессенджера">
    <div class="iwt-msg__title">Куда написать?</div>

    <a class="iwt-msg__link"
       href="https://wa.me/79285550048?text=%D0%9F%D1%80%D0%B8%D0%B2%D0%B5%D1%82%20%D1%81%20%D1%81%D0%B0%D0%B9%D1%82%D0%B0%20iwt.ru"
       target="_blank" rel="noopener noreferrer"
       data-messenger="whatsapp" data-placement="float">
      <span class="iwt-msg__ico iwt-msg__ico--wa" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true">
          <path d="M20.5 3.5A11 11 0 0 0 2.1 17.2L1 23l5.9-1.1A11 11 0 1 0 20.5 3.5zm-8.5 17a9 9 0 0 1-4.6-1.3l-.3-.2-3.5.7.7-3.4-.2-.3A9 9 0 1 1 12 20.5zm5-5.3c-.3-.1-1.6-.8-1.9-.9s-.4-.1-.6.1-.7.9-.8 1-.3.2-.6.1a7.4 7.4 0 0 1-2.2-1.4 8.2 8.2 0 0 1-1.5-1.9c-.2-.3 0-.5.1-.6l.4-.5c.1-.1.2-.3.3-.4s0-.3 0-.4-.6-1.5-.8-2-.2-.5-.5-.5h-.4c-.2 0-.4.1-.6.3s-.8.8-.8 1.9.8 2.2.9 2.3a9.5 9.5 0 0 0 3.5 2.9c1.3.6 1.8.6 2.4.5.4-.1 1.6-.6 1.8-1.3s.2-1.1.2-1.2-.2-.2-.4-.3z"/>
        </svg>
      </span>
      <span>WhatsApp<span class="iwt-msg__hint">AI-помощник IWT</span></span>
    </a>

    <a class="iwt-msg__link"
       href="https://max.ru/id0541026800_bot?start=site"
       target="_blank" rel="noopener noreferrer"
       data-messenger="max" data-placement="float">
      <span class="iwt-msg__ico iwt-msg__ico--max" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true">
          <path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm1 14.5h-2V11h2v5.5zm0-7h-2V7h2v2.5z"/>
        </svg>
      </span>
      <span>MAX<span class="iwt-msg__hint">Бот IWT</span></span>
    </a>
  </div>

  <button type="button" class="iwt-msg__btn" id="iwt-msg-btn"
          aria-expanded="false" aria-controls="iwt-msg-panel" aria-label="Задать вопрос">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
      <path d="M21 12a8.5 8.5 0 0 1-12.3 7.6L3 21l1.5-5.2A8.5 8.5 0 1 1 21 12z"/>
    </svg>
  </button>
</div>

<script>
(function () {
  var root = document.getElementById("iwt-msg");
  var btn = document.getElementById("iwt-msg-btn");
  if (!root || !btn) return;

  function closeMenu() {
    root.classList.remove("is-open");
    btn.setAttribute("aria-expanded", "false");
  }

  function toggleMenu() {
    var open = root.classList.toggle("is-open");
    btn.setAttribute("aria-expanded", open ? "true" : "false");
  }

  btn.addEventListener("click", function (e) {
    e.stopPropagation();
    toggleMenu();
  });

  document.addEventListener("click", function (e) {
    if (!root.contains(e.target)) closeMenu();
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeMenu();
  });
})();
</script>
<!-- ========== /IWT messenger float ========== -->
```

---

## 5. Приёмка (чек-лист для админа)

- [ ] Кнопка видна на главной, в каталоге и на карточке товара (десктоп + мобильный).
- [ ] Клик по кнопке открывает меню WhatsApp / MAX.
- [ ] WhatsApp открывает чат с `+7 928 555-00-48`, в поле уже есть текст «Привет с сайта iwt.ru».
- [ ] MAX открывает бота `id0541026800_bot`.
- [ ] На телефоне кнопка не перекрывает корзину / нижнее меню.
- [ ] Кеш Bitrix сброшен; на проде проверено в режиме инкогнито.

---

## 6. Контакты по задаче

При вопросах по ссылкам/логике ботов — команда IWT AI Sales Platform.  
Изменения ссылок: только в двух `href` внутри блока выше.

**WhatsApp-бот:** `+7 928 555-00-48`  
**MAX-бот:** `https://max.ru/id0541026800_bot`  
**Бизнес-WhatsApp (не для кнопки сайта):** `+7 903 488-00-77`
