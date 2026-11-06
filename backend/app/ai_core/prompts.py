SYSTEM_PROMPT = """
You are an AI sales assistant for iwt.ru.
Use only confirmed company data.
Never invent prices, stock, delivery dates, characteristics, or links.
If confirmed data is missing, request clarification and hand off to a manager.
Respond in Russian by default.
""".strip()


SAFE_HANDOFF_MESSAGE = (
    "Мне нужно уточнить эту информацию у специалиста. "
    "Я передам ваш запрос менеджеру."
)

STOCK_PRICE_GUIDANCE_MESSAGE = (
    "Наличие и цены вы можете посмотреть на сайте IWT https://www.iwt.ru/ "
    "или связаться с менеджером по телефону +7 (8722) 56-06-06, "
    "WhatsApp +79034770088 "
    "или по почте info@iwt.ru."
)

CATEGORY_PRICE_NARROWING_MESSAGE_TEMPLATE = (
    "Есть разные {category}. Уточните модель, бренд или бюджет — и я подберу варианты с актуальными "
    "ценами и наличием из каталога IWT."
)

NO_BUYBACK_MESSAGE = (
    "Нет. IWT не скупает и не выкупает технику (в том числе ноутбуки и компьютеры), "
    "не принимает б/у в зачёт и не делает trade-in.\n\n"
    "Мы продаём новую технику. Подобрать товар можно на сайте https://www.iwt.ru/ "
    "или с помощью менеджера."
)

GREETING_MESSAGE = (
    "Здравствуйте! 😊\n\n"
    "Я помощник интернет-магазина IWT.ru.\n"
    "Чем могу помочь? Могу помочь подобрать товар, узнать характеристики, "
    "условия доставки или передать вопрос менеджеру."
)

THANKS_MESSAGE = (
    "Пожалуйста! Если понадобится помощь с подбором товара, доставкой или оплатой — напишите."
)

PRODUCT_CLARIFY_MESSAGE = (
    "Подскажу по товару. Уточните, пожалуйста, модель, бренд или артикул — "
    "тогда подберу подходящие варианты из каталога IWT."
)

CARTRIDGE_CLARIFY_MESSAGE = (
    "Картриджи есть в ассортименте. Для точного подбора напишите модель принтера "
    "(например, HP LaserJet M404) или артикул картриджа."
)
