#!/usr/bin/env python3
"""一次性生成 data/labeled_email_testset：dataset.json、manifest.csv、emails/*.txt（无标签泄露）。"""
from __future__ import annotations

import csv
import json
import os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT_DIR = os.path.join(ROOT, "data", "labeled_email_testset")
EMAIL_DIR = os.path.join(OUT_DIR, "emails")


def write_email(eid: str, subject: str, body: str) -> None:
    text = f"Subject: {subject}\n\nBody:\n{body.strip()}\n"
    with open(os.path.join(EMAIL_DIR, f"{eid}.txt"), "w", encoding="utf-8") as f:
        f.write(text)


def main() -> None:
    os.makedirs(EMAIL_DIR, exist_ok=True)
    for name in os.listdir(EMAIL_DIR):
        os.remove(os.path.join(EMAIL_DIR, name))

    items = []
    specs: list[tuple[str, str, str | None, str, str, str]] = [
        ("E001", "ham", "verify_code", "双因素验证码", "Your security code: 482917", "Hello,\n\nUse this one-time code to finish signing in:\n\n482917\n\nThis code expires in 10 minutes."),
        ("E002", "ham", "verify_code", "密码重置 PIN", "Password reset PIN", "Your password reset PIN is 739204. Enter it on the reset page within 15 minutes."),
        ("E003", "ham", "updates", "订单发货", "Your order has shipped", "Thanks for your purchase.\n\nYour order #A-10432 has shipped. Tracking: 1Z999AA10123456784."),
        ("E004", "ham", "updates", "预约提醒", "Appointment reminder", "Reminder for your appointment on Tuesday at 10:30 AM.\n\nLocation: Downtown Clinic, Room 3B."),
        ("E005", "ham", "promotions", "会员折扣", "Member weekend sale", "Enjoy an extra 15% off this weekend on selected items. Use code MEMBER15 at checkout."),
        ("E006", "ham", "promotions", "限时活动", "Flash sale ends tonight", "Last chance: up to 40% off home goods until midnight on our store."),
        ("E007", "ham", "social_media", "好友请求", "You have new friend requests", "Alex, Sam, and Jordan want to connect. Open the app to accept or decline."),
        ("E008", "ham", "social_media", "群组摘要", "Weekly digest from your groups", "Here is what happened in your groups this week: 12 new posts and 4 events."),
        ("E009", "ham", "forum", "帖子移动通知", "Your post was moved", "Moderator note: your thread was moved to Technical Support to help others find answers."),
        ("E010", "ham", "forum", "社区守则", "Community guidelines update", "We updated our guidelines to clarify respectful discussion and spam policies."),
        ("E011", "spam", None, "仿冒银行", "URGENT: verify your account", "Your account is locked. Verify now at http://secure-bank-login-fake.example/login\nEnter your password and card number."),
        ("E012", "spam", None, "仿冒快递", "Package delivery failed", "Your package could not be delivered. Pay redelivery fee at http://fake-parcel-pay.example/track"),
        ("E013", "spam", None, "中奖诈骗", "You won a prize", "CONGRATULATIONS. Send your bank details and processing fee to release your prize."),
        ("E014", "spam", None, "高收益骗局", "Guaranteed returns", "Deposit today on instant-profit-scam.example for guaranteed weekly returns. No risk."),
        ("E015", "ham", "updates", "电子收据", "Receipt for your payment", "Thank you. We received your payment of $42.18. Receipt ID: RCP-908812."),
        ("E016", "ham", "promotions", "边界促销", "Spring sale newsletter", "Our spring sale is live. Free shipping on orders over $50 with code SPRINGSHIP."),
        ("E017", "spam", None, "短链垃圾", "Act now", "Limited time. Open link now.\n\nbit.ly/x7K9mQ2"),
        ("E018", "ham", "verify_code", "登录验证码", "Sign-in verification code", "Your sign-in verification code is 628451. If you did not attempt to sign in, reset your password."),
        ("E019", "ham", "verify_code", "Apple 验证码风格", "Apple ID verification", "Your Apple ID verification code is 204881. Do not share this code with anyone."),
        ("E020", "ham", "verify_code", "Microsoft 账户", "Microsoft account security", "Use code 889201 to verify your identity for password change."),
        ("E021", "ham", "updates", "航班变更", "Flight update", "Your flight AA 245 has a new departure time: 6:40 PM. See airline app for details."),
        ("E022", "ham", "updates", "订阅续费提醒", "Subscription renewing soon", "Your annual plan renews on June 1. Manage billing in account settings."),
        ("E023", "ham", "updates", "会议室预订", "Room booking confirmed", "Conference room B12 is booked for you tomorrow 2:00-3:00 PM."),
        ("E024", "ham", "promotions", "生日礼券", "Birthday reward inside", "Happy birthday! Enjoy 20% off your next purchase with code BDAY20."),
        ("E025", "ham", "promotions", "新品上架", "New arrivals this week", "Discover new arrivals in jackets and sneakers. Free returns within 30 days."),
        ("E026", "ham", "social_media", "照片提及", "You were tagged in photos", "You appear in 6 new photos from the weekend hike album."),
        ("E027", "ham", "social_media", "活动邀请", "Event invite: book club", "You are invited to Thursday book club at 7 PM. RSVP in the events tab."),
        ("E028", "ham", "forum", "回复通知", "New reply to your thread", "User PixelArtist replied to your thread about home server setup."),
        ("E029", "ham", "forum", "徽章成就", "You earned a new badge", "Congratulations! You earned the Helpful Contributor badge after 50 accepted answers."),
        ("E030", "spam", None, "仿冒 PayPal", "Unusual sign-in activity", "We locked your PayPal. Confirm identity at paypaI-security.example (lookalike domain)."),
        ("E031", "spam", None, "勒索风格", "We have your data", "Pay 0.5 BTC or we release your files. Send to wallet address within 48 hours."),
        ("E032", "spam", None, "仿冒 Netflix", "Payment failed", "Update payment method at netflix-billing-support.example or your account will be suspended."),
        ("E033", "spam", None, "药品垃圾", "Cheap meds online", "Buy prescription drugs without prescription. Fast shipping worldwide."),
        ("E034", "spam", None, "股票喊单", "Hot stock tip", "This ticker will triple next week. Buy before market open. Unsubscribe STOP."),
        ("E035", "spam", None, "工作机会诈骗", "Remote job offer", "Earn $5000 weekly working from home. Send $99 training fee to start immediately."),
        ("E036", "ham", "verify_code", "银行转账验证码", "Wire transfer authorization", "Enter code 551902 to authorize wire transfer of $250 to savings."),
        ("E037", "ham", "updates", "云服务账单", "Your monthly invoice", "Your May invoice for CloudHost is $118.42. Download PDF from billing portal."),
        ("E038", "ham", "updates", "课程开课提醒", "Course starts Monday", "Your course Introduction to Data Ethics begins Monday 9 AM. Zoom link in LMS."),
        ("E039", "ham", "promotions", "免运费门槛", "Free shipping unlocked", "You are $12 away from free shipping. Add items to cart before midnight."),
        ("E040", "ham", "social_media", "关注推荐", "People you may know", "We found 8 people you may know based on your school and workplace."),
    ]

    for eid, g1, g2, note, subj, body in specs:
        write_email(eid, subj, body)
        items.append(
            {
                "id": eid,
                "email_file": f"emails/{eid}.txt",
                "gold_stage1": g1,
                "gold_stage2": g2,
                "note_zh": note,
            }
        )

    dataset = {
        "schema_version": 1,
        "description": "答案在 dataset.json；emails 内仅 Subject/Body，不含类别标签字样。",
        "items": items,
    }
    with open(os.path.join(OUT_DIR, "dataset.json"), "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    csv_path = os.path.join(OUT_DIR, "manifest.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "email_file", "gold_stage1", "gold_stage2", "note_zh"])
        for it in items:
            w.writerow([it["id"], it["email_file"], it["gold_stage1"], it.get("gold_stage2") or "", it.get("note_zh", "")])

    old_manifest = os.path.join(OUT_DIR, "manifest.json")
    if os.path.isfile(old_manifest):
        os.remove(old_manifest)

    print(f"Wrote {len(items)} emails to {EMAIL_DIR}")
    print(f"Wrote {OUT_DIR}/dataset.json and manifest.csv")


if __name__ == "__main__":
    main()
