"""模板化合成数据生成器：生成 NER 标注数据和分类训练数据。"""

from __future__ import annotations

import json
import random
import csv
from pathlib import Path
from typing import List, Dict, Tuple

COMPANIES = [
    "字节跳动", "腾讯", "阿里巴巴", "百度", "美团", "京东", "华为", "小米",
    "网易", "快手", "滴滴", "拼多多", "蚂蚁集团", "微软中国", "谷歌中国",
    "亚马逊中国", "苹果中国", "英特尔", "高盛", "摩根士丹利", "中金公司",
    "招商银行", "平安科技", "大疆创新", "商汤科技", "旷视科技", "寒武纪",
    "蔚来汽车", "理想汽车", "小鹏汽车", "比亚迪", "宁德时代", "中芯国际",
    "联想集团", "OPPO", "vivo", "荣耀", "携程", "去哪儿", "饿了么",
    "哔哩哔哩", "知乎", "小红书", "得物", "货拉拉", "顺丰科技",
    "海康威视", "科大讯飞", "三七互娱", "米哈游", "莉莉丝",
]

POSITIONS = [
    "后端开发工程师", "前端开发工程师", "算法工程师", "数据分析师",
    "产品经理", "测试工程师", "运维工程师", "Java开发", "Python开发",
    "Go开发工程师", "C++开发", "iOS开发", "Android开发", "全栈工程师",
    "机器学习工程师", "NLP工程师", "计算机视觉工程师", "大数据工程师",
    "云计算工程师", "安全工程师", "架构师", "技术总监", "项目经理",
    "UI设计师", "交互设计师", "数据工程师", "DevOps工程师",
    "嵌入式开发", "FPGA工程师", "芯片设计工程师",
]

ROUNDS = [
    "一面", "二面", "三面", "HR面", "终面", "技术面试",
    "笔试", "电话面试",
]

LOCATIONS = [
    "北京市海淀区中关村软件园", "北京市朝阳区望京SOHO",
    "上海市浦东新区张江高科", "上海市徐汇区漕河泾",
    "深圳市南山区科技园", "深圳市福田区CBD",
    "杭州市余杭区未来科技城", "杭州市西湖区",
    "广州市天河区珠江新城", "成都市高新区天府软件园",
    "武汉市东湖高新区光谷", "南京市雨花台区软件谷",
    "线上（腾讯会议）", "线上（Zoom）", "线上（飞书）",
    "线上（Teams）", "线上（钉钉）",
]

# PLACEHOLDER_TIME_FORMATS

TIME_FORMATS = [
    "2024年{m}月{d}日 {h}:{mi}",
    "{m}月{d}日（周{w}）{h}:{mi}",
    "{m}/{d} {h}:{mi}",
    "{m}月{d}号 下午{h2}点",
    "{m}月{d}号 上午{h3}点",
    "本周{w2} {h}:{mi}",
    "下周{w2} {h}:{mi}",
]

WEEKDAYS = ["一", "二", "三", "四", "五"]
WEEKDAYS2 = ["周一", "周二", "周三", "周四", "周五"]


def _random_time() -> str:
    fmt = random.choice(TIME_FORMATS)
    m = random.randint(1, 12)
    d = random.randint(1, 28)
    h = random.randint(9, 18)
    mi = random.choice(["00", "30"])
    h2 = random.randint(1, 6)
    h3 = random.randint(9, 11)
    w = random.choice(WEEKDAYS)
    w2 = random.choice(WEEKDAYS2)
    return fmt.format(m=m, d=d, h=h, mi=mi, h2=h2, h3=h3, w=w, w2=w2)


INTERVIEW_TEMPLATES = [
    "您好，恭喜您通过{company}的{position}岗位简历筛选，{round}安排在{time}，地点：{location}。请准时参加。",
    "{company}邀请您参加{position}的{round}，时间：{time}，地点：{location}。如有问题请回复此邮件。",
    "尊敬的候选人，您申请的{company}{position}职位已进入{round}环节，面试时间为{time}，面试地点：{location}。",
    "通知：{company}{position}岗位{round}定于{time}进行，地址：{location}，请提前10分钟到达。",
    "您好！{company}HR通知您，{position}的{round}已安排，时间{time}，{location}，届时请携带简历。",
    "面试邀请：{company}诚邀您参加{position}{round}，{time}，{location}。期待您的到来！",
]

APPLIED_TEMPLATES = [
    "您好，您投递的{company}{position}岗位已收到，我们将尽快审核您的简历。",
    "感谢您申请{company}的{position}职位，您的简历已成功提交，请耐心等待后续通知。",
    "投递确认：您已成功申请{company}{position}岗位，HR将在3-5个工作日内回复。",
    "您好，{company}已收到您{position}岗位的求职申请，感谢您的关注。",
    "申请确认函：您对{company}{position}的申请已记录，祝您求职顺利。",
]

WRITTEN_TEST_TEMPLATES = [
    "您好，{company}邀请您参加{position}岗位的在线笔试，时间：{time}，请登录指定平台完成。",
    "笔试通知：{company}{position}笔试安排在{time}，时长120分钟，请提前准备好网络环境。",
    "{company}{position}在线测评通知：请于{time}前完成在线笔试，链接将在考试前发送。",
    "您好，恭喜进入{company}{position}笔试环节，笔试时间{time}，请注意查收后续邮件。",
]

OFFER_TEMPLATES = [
    "恭喜您！{company}正式向您发出{position}岗位的录用通知(Offer)，期待您的加入！",
    "Offer Letter：经过综合评估，{company}决定录用您为{position}，薪资待遇详见附件。",
    "您好，很高兴通知您已通过{company}{position}的全部面试流程，现正式发出录用意向。",
    "录用通知：{company}诚挚邀请您加入我们的团队，担任{position}一职。",
]

REJECTED_TEMPLATES = [
    "很遗憾通知您，经过慎重考虑，{company}{position}岗位未能与您达成匹配，感谢您的参与。",
    "您好，感谢您参加{company}{position}的面试，遗憾的是本次未能通过，祝您前程似锦。",
    "通知：您申请的{company}{position}职位，经评估后暂不符合当前需求，欢迎未来再次申请。",
    "尊敬的候选人，{company}{position}岗位竞争激烈，很遗憾本次未能录用，感谢您的时间。",
]

NOT_JOB_TEMPLATES = [
    "您的{company}账号于{time}在新设备登录，如非本人操作请立即修改密码。",
    "您在{company}的订单已发货，预计{time}送达，请注意查收。",
    "【{company}】您的验证码是{code}，5分钟内有效，请勿泄露。",
    "{company}双十一大促开始啦！全场满300减50，活动截止{time}。",
    "您关注的{company}论坛帖子有新回复，点击查看详情。",
    "【{company}通知】系统将于{time}进行维护升级，届时服务暂停。",
    "您的{company}会员即将到期，续费享8折优惠。",
    "{company}周报：本周团队完成了3个迭代，详情请查看附件。",
]


def _tokenize(text: str) -> List[str]:
    tokens: List[str] = []
    buf = ""
    for ch in text:
        if ch.isascii() and ch.isalpha():
            buf += ch
        else:
            if buf:
                tokens.append(buf)
                buf = ""
            if ch.strip():
                tokens.append(ch)
    if buf:
        tokens.append(buf)
    return tokens


def _label_tokens(tokens: List[str], entities: Dict[str, str]) -> List[str]:
    labels = ["O"] * len(tokens)
    text = "".join(tokens)

    for ent_type, ent_value in entities.items():
        ent_tokens = _tokenize(ent_value)
        if not ent_tokens:
            continue
        for i in range(len(tokens) - len(ent_tokens) + 1):
            if tokens[i:i + len(ent_tokens)] == ent_tokens:
                labels[i] = f"B-{ent_type}"
                for j in range(1, len(ent_tokens)):
                    labels[i + j] = f"I-{ent_type}"
                break
    return labels


def generate_ner_data(n_samples: int = 4000, seed: int = 42) -> List[Dict]:
    random.seed(seed)
    samples: List[Dict] = []

    for _ in range(n_samples):
        company = random.choice(COMPANIES)
        position = random.choice(POSITIONS)
        round_ = random.choice(ROUNDS)
        location = random.choice(LOCATIONS)
        time_ = _random_time()

        template = random.choice(INTERVIEW_TEMPLATES)
        text = template.format(
            company=company, position=position,
            round=round_, time=time_, location=location,
        )
        tokens = _tokenize(text)
        entities = {
            "COMPANY": company,
            "POSITION": position,
            "ROUND": round_,
            "TIME": time_,
            "LOCATION": location,
        }
        labels = _label_tokens(tokens, entities)
        samples.append({"tokens": tokens, "labels": labels})

    return samples


def generate_classifier_data(n_per_class: int = 600, seed: int = 42) -> List[Dict]:
    random.seed(seed)
    samples: List[Dict] = []

    stage_templates = {
        "applied": APPLIED_TEMPLATES,
        "written_test": WRITTEN_TEST_TEMPLATES,
        "interview": INTERVIEW_TEMPLATES,
        "offer": OFFER_TEMPLATES,
        "rejected": REJECTED_TEMPLATES,
    }

    for stage, templates in stage_templates.items():
        for _ in range(n_per_class):
            company = random.choice(COMPANIES)
            position = random.choice(POSITIONS)
            round_ = random.choice(ROUNDS)
            location = random.choice(LOCATIONS)
            time_ = _random_time()
            template = random.choice(templates)
            text = template.format(
                company=company, position=position,
                round=round_, time=time_, location=location,
            )
            samples.append({"text": text, "label": stage, "is_job": True})

    for _ in range(n_per_class * 2):
        company = random.choice(COMPANIES)
        time_ = _random_time()
        code = str(random.randint(100000, 999999))
        template = random.choice(NOT_JOB_TEMPLATES)
        text = template.format(company=company, time=time_, code=code)
        samples.append({"text": text, "label": "not_job", "is_job": False})

    random.shuffle(samples)
    return samples


def save_ner_data(output_dir: Path, n_samples: int = 4000, seed: int = 42) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    samples = generate_ner_data(n_samples, seed)

    train_split = int(len(samples) * 0.85)
    train_path = output_dir / "ner_train.jsonl"
    test_path = output_dir / "ner_test.jsonl"

    with open(train_path, "w", encoding="utf-8") as f:
        for s in samples[:train_split]:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    with open(test_path, "w", encoding="utf-8") as f:
        for s in samples[train_split:]:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    return output_dir


def save_classifier_data(output_dir: Path, n_per_class: int = 600, seed: int = 42) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    samples = generate_classifier_data(n_per_class, seed)

    train_split = int(len(samples) * 0.85)
    train_path = output_dir / "job_cls_train.csv"
    test_path = output_dir / "job_cls_test.csv"

    for path, data in [(train_path, samples[:train_split]), (test_path, samples[train_split:])]:
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["text", "label", "is_job"])
            writer.writeheader()
            writer.writerows(data)

    return output_dir


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent.parent.parent / "data" / "job"
    print(f"Generating data to {out}")
    save_ner_data(out)
    save_classifier_data(out)
    print("Done.")
