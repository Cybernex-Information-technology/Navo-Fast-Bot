"""
Yuklash jarayonida foydalanuvchiga ko'rsatiladigan kreativ,
xushchaqchaq va kayfiyatni ko'taruvchi xabarlar to'plami.
"""
import random

FUN_PHRASES = [
    "⏳ Yuklanmoqda... Shu orada bir tabassum qiling 😊",
    "🎶 Yaxshi musiqa — yaxshi kayfiyat kafolati!",
    "😄 Kulib turing, kulgi inson umrini uzaytiradi ✨",
    "🚀 Navo serverlari 100% tezlikda ishlayapti, ozgina sabr...",
    "☕ Bir qultum choy yoki kofe ichib turing, deyarli tayyor bo'ldi!",
    "🌟 Bugun siz uchun ajoyib va omadli kun bo'lsin!",
    "🎧 Sifatli audio sizning didingizga mos keladi deb umid qilamiz 🎵",
    "⚡ Sekundlar qoldi... Fayl telegraf simlari bo'ylab uchib kelmoqda 🕊️",
    "🍉 Dunyodagi eng totli narsa nima? Albatta, tez yuklangan video! 😄",
    "💡 Bilasizmi? Musiqa tinglash miya faoliyatini 30% ga yaxshilaydi 🧠",
    "🎯 Eng sara kontentni siz uchun saralab yuklayapmiz...",
    "😎 Sabr qilgan yetar murodga, oz qoldi do'stim!",
    "✨ Har bir soniyangiz maroqli o'tsin!",
    "🛸 Kosmik tezlikda yuklab, Telegram tarmog'iga uzatyapmiz...",
    "🪄 Sehrli tayoqcha ishga tushdi, soniyalarda tayyor!",
    "🏖️ O'zingizni erkin tuting, og'ir ishni botga qo'yib bering 😉",
    "🔥 Sifat buzilmasligi uchun oxirgi piksellar sayqallanmoqda...",
    "🎼 Quloqchinlarni tayyorlab turing, hozir ajoyib trek keladi!",
    "🌈 Kayfiyatingiz doim a'lo, yuzingizda kulgu bo'lsin!",
    "🏁 Marra chizig'iga yetib keldik, yuklanish yakunlanmoqda..."
]


def get_random_phrase() -> str:
    return random.choice(FUN_PHRASES)
