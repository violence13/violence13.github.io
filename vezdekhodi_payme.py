from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode, Message, CallbackQuery, ContentType, \
    PreCheckoutQuery, SuccessfulPayment, LabeledPrice
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from db import get_tour_list, get_tour_info, update_booking_status, save_booking, get_user_data, get_user_language
from localization import get_message
from states.Booking import BookingStates, DeclineReason

async def confirm_booking(booking_id):
    # Получение информации о заявке из базы данных
    booking_info = get_booking_info(booking_id)
    if booking_info:
        user_id = booking_info['user_id']
        user_language = get_user_language(user_id)

        tour_id = booking_info['tour_id']
        tour_info = get_tour_info(tour_id)
        tour_title = tour_info[1]  # Заголовок тура
        tour_date = tour_info[5]  # Дата тура
        tour_price = tour_info[4]  # Цена тура

        update_booking_status(booking_id, 'подтверждена')
        if user_language == 'ru':
            message_text = (f"Ваша заявка на тур {tour_title} на дату {tour_date} успешно подтверждена."
                            f" Теперь вы можете произвести оплату ({tour_price}).")
        else:
            message_text = (
                f"Sizning {tour_title} ga qoldirgan so'rovingiz muvaffaqqiyatli tasdiqlandi. Endi to'lovni ({tour_price}) amalga oshirishingiz mumkin.")

        if user_language == 'ru':
            keyboard = InlineKeyboardMarkup().add(
                InlineKeyboardButton("Оплатить", callback_data=f'pay_{booking_id}')
            )
        else:
            keyboard = InlineKeyboardMarkup().add(
                InlineKeyboardButton("To'lash", callback_data=f'pay_{booking_id}')
            )

        await bot.send_message(user_id, message_text, reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data.startswith('pay_'))
async def process_payment(callback_query: types.CallbackQuery):
    booking_id = callback_query.data.split('_')[1]
    await initiate_payment(callback_query.message, booking_id)


async def initiate_payment(message, booking_id):
    # Есть функция для получения информации о туре
    booking_info = get_booking_info(booking_id)
    tour_info = get_tour_info(booking_info['tour_id'])

    # Информация для счета
    title = tour_info[1]  # Название тура
    description = "Оплата за тур: " + title
    currency = "UZS"  # Валюта платежа
    total_amount = int(float(tour_info[4]) * 100)  # Цена тура в тийин (1 сум = 100 тийин)

    prices = [LabeledPrice("Основная стоимость", total_amount)]

    # Указываем провайдера платежей и стартовый параметр для уникальности
    provider_token = 'PROVIDER_TOKEN_HERE'  # Токен провайдера Payme
    start_parameter = 'tour-payment-' + str(booking_id)

    await bot.send_invoice(
        message.chat.id,
        title=title,
        description=description,
        provider_token=provider_token,
        currency=currency,
        prices=prices,
        start_parameter=start_parameter,
        payload=str(booking_id)  # Payload, который будет возвращен в PreCheckoutQuery
    )


@dp.pre_checkout_query_handler(lambda query: True)
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    # Здесь можно добавить проверки перед финализацией платежа, если необходимо
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@dp.message_handler(content_types=ContentType.SUCCESSFUL_PAYMENT)
async def process_successful_payment(message: types.Message):
    # Здесь обработка успешного платежа
    successful_payment: SuccessfulPayment = message.successful_payment
    booking_id = successful_payment.invoice_payload  # Payload, который мы отправили в send_invoice

    # Подтверждение бронирования или другие действия
    await confirm_booking_or_other_actions(booking_id)

    await message.reply(
        f"Спасибо за вашу оплату {successful_payment.total_amount / 100} {successful_payment.currency}. Ваш заказ на тур подтвержден.")


async def confirm_booking_or_other_actions(booking_id):
    # Получение информации о заявке из базы данных
    booking_info = get_booking_info(booking_id)
    if booking_info:
        # Обновление статуса заявки на "оплачена"
        update_booking_status(booking_id, 'оплачена')

        user_id = booking_info['user_id']
        tour_id = booking_info['tour_id']
        tour_info = get_tour_info(tour_id)
        tour_title = tour_info[1]  # Название тура

        # Отправляем уведомление пользователю о подтверждении его заявки после оплаты
        user_language = get_user_language(user_id)
        message_text = get_message(user_language, "final_confirmation").format(tour_title=tour_title)
        await bot.send_message(user_id, message_text)

        # Также можете уведомить администратора о завершении оплаты
        admin_message = f"Оплата за тур {tour_title} от пользователя {user_id} успешно получена."
        admin_id = 1111
        await bot.send_message(admin_id, admin_message)


