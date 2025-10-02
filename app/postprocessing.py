topics_to_replace = {
    "Обслуживание в банкоматах" : "Банкоматы",
    "Обслуживание в банкомате" : "Банкоматы",
    "Дебетовая карта «Мир»" : "Умная дебетовая карта «Мир»",
    "UnionPay" : "Карта UnionPay",
    "Карта Union Pay" : "Карта UnionPay",
    "Карты UnionPay" : "Карта UnionPay",
    "Программа приведи друга" : "Программы лояльности",
    "Программа лояльности" : "Программы лояльности",
    "Индивидуальный пенсионный план" : "Инвестиционные продукты",
    "Кредитование" : "Кредиты",
    "Потребительский кредит" : "Кредиты",
    "Умная кредитная карта" : "Кредитные карты",
    "Кредиты наличными" : "Кредит наличными",
    "Кредиты наличными" : "Кредит наличными",
    "Акции банка" : "Акции",
    "Брокерское обслуживание" : "Брокерские услуги",
    "Накопительный счет" : "Накопительные счета",
    "Накопительный счет «Премиум»" : "Накопительный счёт «Премиум»",
    "Газпромбанк Мобайл" : "Мобильное приложение",
    "Доставка карт" : "Курьерская доставка карт",
    "Доставка карты" : "Курьерская доставка карт",
    "Доставка продуктов" : "Курьерская доставка карт",
    "«Премиум»" : "Газпромбанк Премиум",
    "Подписка Премиум" : "Газпромбанк Премиум",
    "Премиум" : "Газпромбанк Премиум",
    "Программа привилегий" : "Газпромбанк Привилегии",
    "Привилегии" : "Газпромбанк Привилегии",
    "Дополнительные услуги" : "Другие услуги банка",
    "Gazprom Pay (оплата телефоном)" : "Gazprom Pay",
    "Газпромбанк Travel (покупка авиабилетов/отелей)" : "Газпромбанк Travel",
    "GorodPay (оплата общественного транспорта)" : "GorodPay",
}


topics_subtopics = {
    "Офисное обслуживание" : [],
    "Банкоматы" : [],
    "Дистанционное обслуживание" : [],
    "Дебетовые карты" : [
        "Денежные переводы",
        "Карта UnionPay",
        "Умная дебетовая карта «Мир»",
        "Премиальная карта Mir Supreme",
        "Карта для автолюбителей «Газпромбанк—Газпромнефть»",
        "Виртуальная дебетовая карта ГПБ&ФК «Зенит»",
        "Дебетовая Пенсионная карта",
    ],
    "Курьерская доставка карт" : [],
    "Кредитные карты" : [
        "Кредитная карта 180 дней Премиум",
    ],
    "Вклады" : [
        "Вклад «Копить»",
        "Вклад «В Плюсе»",
        "Вклад «Новые деньги»",
        "Вклад «Ключевой момент»",
        "Вклад «Расширяй возможности»",
        "Социальный вклад",
    ],
    "Кредиты" : [
        "Кредит наличными",
        "Кредит наличными под залог недвижимости",
        "Кредит под залог автомобиля",
        "Дачный кредит",
        "Кредит на образование",
        "Кредит наличными для бюджетников",
    ],
    "Автокредиты" : [],
    "Страховые и сервисные продукты" : [],
    "Ипотека" : [
        "Ипотека для IT-специалистов",
        "Семейная ипотека",
        "Дальневосточная ипотека",
        "Ипотека на Новостройку",
    ],
    "Мобильное приложение" : [],
    "Реструктуризация/Рефинансирование" : [
        "Рефинансирование кредитов",
        "Реструктуризация кредитов",
        "Рефинансирование ипотеки",
        "Реструктуризация ипотеки",
    ],
    "Акции и бонусы" : [
        "Газпром Бонус",
        "Газпромбанк Привилегии",
        "Кэшбэк",
        "Акции",
        "Программы лояльности",
    ],
    "Газпромбанк Премиум" : [
        "Персональный менеджер",
        "Консьерж-сервис",
        "Премиальное обслуживание",
        "Кредитная карта 180 дней Премиум",
        "Премиальная карта Mir Supreme",
        "Накопительный счёт «Премиум»",
    ],
    "Обмен валют" : [],
    "Накопительные счета" : [
        "Накопительный счёт «Ежедневная выгода»",
        "Накопительный счёт «Ежедневный процент»",
        "Накопительный счёт «Премиум»",
        "Накопительный счёт Социальный счет",
    ],
    "Другие услуги банка" : [
        "Газпромбанк Travel",
        "Gazprom Pay",
        "GorodPay",
        "Газпромбанк Инвестиции",
        "Инвестиционные продукты",
        "Брокерские услуги",
        "Депозитарные услуги",
        "Аренда сейфовых ячеек",
    ]
}

main_topics = list(topics_subtopics.keys())

topics_subtopics_flatten = []
for topic in topics_subtopics:
    topics_subtopics_flatten.append(topic)
    topics_subtopics_flatten.extend(topics_subtopics[topic])
    
    
# topics_subtopics_flatten
topics_subtopics_flatten_set = set(topics_subtopics_flatten)



def identify_topic_by_subtopic(selected_topic, return_if_subtopic=True):
    selected_topic = selected_topic.strip()
    if selected_topic in topics_subtopics:
        return [selected_topic]
    
    topic_exists = False
    
    identified_subtopics = []
    for topic in topics_subtopics:
        subtopics = topics_subtopics[topic]
        if selected_topic in subtopics:
            topic_exists = True
            identified_subtopics.append(topic)
    
    if topic_exists and return_if_subtopic:
        identified_subtopics.append(selected_topic)
    
    return identified_subtopics


def postprocess(topics_sentiments_full, return_subtopics=True):
    updated_topics_sentiments_full = []

    for review in topics_sentiments_full:
        id_name = "id" if ("id" in review) else "reviewId"
        assert id_name in review
        
        new_review_sample = {
            "id" : review[id_name],
            # "id" : review["reviewId"],
            # "summarized_review" : review["summarized_review"]
        }
        pairs = review["topic_sentiment_pairs"]
        unique_topics = set()
        new_pairs = []
        for pair in pairs:
            pair_topic = pair["topic"]
            pair_sentiment = pair["sentiment"]
            
            if pair_topic in topics_to_replace:
                pair_topic = topics_to_replace[pair_topic]
                # if pair_topic not in unique_topics:
                #     unique_topics.add(pair_topic)
            
            identified_topics = identify_topic_by_subtopic(pair_topic, return_subtopics)
            
            for identified_topic in identified_topics:
                if identified_topic not in unique_topics:
                    unique_topics.add(identified_topic)
                    new_pairs.append(
                        {
                            "topic" : identified_topic,
                            "sentiment" : pair_sentiment
                        }
                    )

        new_review_sample["topic_sentiment_pairs"] = new_pairs
        updated_topics_sentiments_full.append(new_review_sample)
    
    return updated_topics_sentiments_full
