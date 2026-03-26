"""
bot.py - Class FCOnlineBot tổng hợp từ tất cả các Mixin.

Thứ tự kế thừa:
  FCOnlineBot → UpgradeMixin → BuyFodderMixin → FCOnlineBotBase (bot_core)
"""
from bot_core import FCOnlineBot as FCOnlineBotBase
from bot_upgrade import UpgradeMixin
from bot_buy import BuyFodderMixin
from bot_insert import InsertMixin as InsertMixin
from bot_insert_mua import InsertMuaMixin

class FCOnlineBot(UpgradeMixin, BuyFodderMixin, InsertMixin, InsertMuaMixin, FCOnlineBotBase):
    """
    Bot tổng hợp đầy đủ:
    - run()             : Auto Đập Thẻ
    - run_buy_fodder()  : Auto Mua Phôi
    - run_insert()      : Auto Chèn (DS Mua)
    """
    pass
