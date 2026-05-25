"""生成 job 类别的训练数据，用于 Stage 2 分类器。"""

import csv
import random
from pathlib import Path

# 复用 data_gen.py 中的模板和词典
COMPANIES = [
    "字节跳动", "腾讯", "阿里巴巴", "百度", "美团", "京东", "华为", "小米",
    "网易", "快手", "滴滴", "拼多多", "蚂蚁集团", "哔哩哔哩", "知乎", "小红书",
    "得物", "货拉拉", "携程", "去哪儿", "饿了么", "顺丰科技", "SHEIN",
    "大疆创新", "商汤科技", "旷视科技", "寒武纪", "地平线", "云从科技",
    "蔚来汽车", "理想汽车", "小鹏汽车", "比亚迪", "宁德时代",
    "米哈游", "莉莉丝", "三七互娱", "网易游戏", "腾讯游戏",
    "微软", "谷歌", "亚马逊", "苹果", "英特尔", "英伟达",
    "高盛", "摩根士丹利", "中金公司", "招商银行", "平安科技",
]

POSITIONS = [
    "后端开发实习生", "前端开发实习生", "算法实习生", "数据分析实习生",
    "产品经理实习生", "测试开发实习生", "Java开发实习生", "Python开发实习生",
    "后端开发工程师", "前端开发工程师", "算法工程师", "数据分析师",
    "产品经理", "测试工程师", "Java开发工程师", "Go开发工程师",
    "机器学习工程师", "NLP工程师", "计算机视觉工程师", "大数据工程师",
    "iOS开发工程师", "Android开发工程师", "全栈工程师", "架构师",
]

ROUNDS = ["一面", "二面", "三面", "HR面", "终面", "技术一面", "技术二面", "主管面"]

LOCATIONS = [
    "北京市海淀区", "上海市浦东新区", "深圳市南山区", "杭州市余杭区",
    "广州市天河区", "成都市高新区", "武汉市东湖高新区", "南京市雨花台区",
    "线上（腾讯会议）", "线上（飞书视频）", "视频面试", "电话面试",
]

TIMES = [
    "2026年5月28日14:00", "2026年6月1日10:30", "5月30日下午3点",
    "6月5日（周四）15:00", "下周三 14:00", "本周五 10:00",
    "2026-06-10 09:30", "6月15日上午10点",
]

# 面试邀约模板
INTERVIEW_TEMPLATES = [
    "您好，恭喜您通过{company}的{position}岗位简历筛选，{round}安排在{time}，地点：{location}。",
    "{company}邀请您参加{position}的{round}，时间：{time}，地点：{location}。",
    "尊敬的候选人，您申请的{company}{position}职位已进入{round}环节，面试时间为{time}。",
    "通知：{company}{position}岗位{round}定于{time}进行，地址：{location}。",
    "面试邀请：{company}诚邀您参加{position}{round}，{time}，{location}。",
    "{company}诚邀你参加{position}岗位的面试。面试时间：{time}，面试轮次：{round}，地点：{location}。",
    "Hi，你已通过{company}{position}的简历筛选，现邀请你参加{round}。面试时间：{time}。",
    "恭喜您通过{company}{position}岗位的前序面试！现通知您参加{round}，时间：{time}，地点：{location}。",
    "【{company}校招】{position}岗位{round}通知，时间：{time}，地点：{location}。",
    "同学你好，恭喜你通过{company}{position}的面试评估，现安排{round}：时间{time}，地点{location}。",
]

# 投递确认模板
APPLIED_TEMPLATES = [
    "您好，您投递的{company}{position}岗位已收到，我们将尽快审核您的简历。",
    "感谢您申请{company}的{position}职位，您的简历已成功提交。",
    "投递确认：您已成功申请{company}{position}岗位，HR将在3-5个工作日内回复。",
    "您好，{company}已收到您{position}岗位的求职申请，感谢您的关注。",
    "【{company}校招】简历投递成功通知，你投递的{position}岗位简历已成功提交。",
    "感谢你对{company}的关注！你申请的{position}职位已进入简历评估阶段。",
    "【投递成功】{company}-{position}，你的简历已成功投递。",
]

# 笔试通知模板
WRITTEN_TEST_TEMPLATES = [
    "您好，{company}邀请您参加{position}岗位的在线笔试，时间：{time}。",
    "笔试通知：{company}{position}笔试安排在{time}，时长120分钟。",
    "{company}{position}在线测评通知：请于{time}前完成在线笔试。",
    "恭喜进入{company}{position}笔试环节，笔试时间{time}。",
    "【{company}校招笔试通知】恭喜你通过{position}岗位的简历筛选！笔试时间：{time}。",
    "Hi，{company}{position}的在线编程测试已开放，时间：{time}。",
    "{company}2026校招{position}岗位笔试通知：笔试时间{time}。",
]

# Offer模板
OFFER_TEMPLATES = [
    "恭喜您！{company}正式向您发出{position}岗位的录用通知(Offer)！",
    "Offer Letter：经过综合评估，{company}决定录用您为{position}。",
    "您好，很高兴通知您已通过{company}{position}的全部面试流程，现正式发出录用意向。",
    "录用通知：{company}诚挚邀请您加入我们的团队，担任{position}一职。",
    "【{company}】录用通知书，恭喜你成功通过{position}岗位的全部面试环节！",
    "Hi，恭喜你拿到{company}的Offer！岗位：{position}。",
    "恭喜！{company}{position}岗位Offer已发出，请查收附件。",
]

# 拒信模板
REJECTED_TEMPLATES = [
    "很遗憾通知您，经过慎重考虑，{company}{position}岗位未能与您达成匹配。",
    "您好，感谢您参加{company}{position}的面试，遗憾的是本次未能通过。",
    "通知：您申请的{company}{position}职位，经评估后暂不符合当前需求。",
    "尊敬的候选人，{company}{position}岗位竞争激烈，很遗憾本次未能录用。",
    "【{company}】面试结果通知，感谢你参加{position}岗位的面试，很遗憾本次未能通过。",
    "Hi，感谢你对{company}的关注，{position}岗位本次暂未匹配成功。",
    "遗憾通知：{company}{position}岗位经综合评定，本次未能录用。",
]


def generate_job_samples(n_per_type: int = 400) -> list:
    """生成求职邮件样本。"""
    samples = []

    # 面试邀约
    for _ in range(n_per_type):
        tpl = random.choice(INTERVIEW_TEMPLATES)
        text = tpl.format(
            company=random.choice(COMPANIES),
            position=random.choice(POSITIONS),
            round=random.choice(ROUNDS),
            time=random.choice(TIMES),
            location=random.choice(LOCATIONS),
        )
        subject = f"【{random.choice(COMPANIES)}】{random.choice(POSITIONS)}面试邀请"
        samples.append((subject, text))

    # 投递确认
    for _ in range(n_per_type // 2):
        tpl = random.choice(APPLIED_TEMPLATES)
        text = tpl.format(
            company=random.choice(COMPANIES),
            position=random.choice(POSITIONS),
        )
        subject = f"【{random.choice(COMPANIES)}】简历投递确认"
        samples.append((subject, text))

    # 笔试通知
    for _ in range(n_per_type // 2):
        tpl = random.choice(WRITTEN_TEST_TEMPLATES)
        text = tpl.format(
            company=random.choice(COMPANIES),
            position=random.choice(POSITIONS),
            time=random.choice(TIMES),
        )
        subject = f"【{random.choice(COMPANIES)}】笔试通知"
        samples.append((subject, text))

    # Offer
    for _ in range(n_per_type // 2):
        tpl = random.choice(OFFER_TEMPLATES)
        text = tpl.format(
            company=random.choice(COMPANIES),
            position=random.choice(POSITIONS),
        )
        subject = f"【{random.choice(COMPANIES)}】录用通知"
        samples.append((subject, text))

    # 拒信
    for _ in range(n_per_type // 2):
        tpl = random.choice(REJECTED_TEMPLATES)
        text = tpl.format(
            company=random.choice(COMPANIES),
            position=random.choice(POSITIONS),
        )
        subject = f"【{random.choice(COMPANIES)}】面试结果通知"
        samples.append((subject, text))

    return samples


def main():
    output_path = Path(__file__).parent.parent.parent.parent / "data" / "job_classification.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    samples = generate_job_samples(n_per_type=500)
    random.shuffle(samples)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "subject", "body", "text", "category", "category_id"])
        for i, (subject, body) in enumerate(samples):
            text = f"{subject} {body}"
            writer.writerow([f"job_{i}", subject, body, text, "job", 5])

    print(f"Generated {len(samples)} job samples to {output_path}")


if __name__ == "__main__":
    main()
