import sys
import asyncio

# 域名后缀黑名单
REMOVE_END = [
    "jsdelivr.net",
    "jsdelivr.com",
    "outlook.com",
    "gh-proxy.com"
]

# 行内容黑名单关键词，含有这些内容的行将被忽略
FILTER_KEYWORDS = [
    "payload:", "rules:", "regexp", "IP-CIDR,", "DOMAIN-KEYWORD,", "PROCESS-NAME,",
    "IP-SUFFIX,", "GEOIP,", "GEOSITE,",
    "#", "!", "/", "【", "】", "[", "]", "$",
    "1drv", "1e100", "abema", "appledaily", "avtb", "beetalk", "blogspot", "dlercloud", "dropbox", "facebook", "fbcdn", "gmail", "google", "instagram", "onedrive", "paypal", "porn", "sci-hub", "skydrive", "spotify", "telegram", "ttvnw", "twitter", "uk-live", "whatsapp", "youtube", "bilibili.com"
]

def clean_line(line: str) -> str:
    """清理行中的空格、无效符号，标准化原始字符串。"""
    for ch in " \"'|^":
        line = line.replace(ch, "")
    return line

def is_filtered_line(line: str) -> bool:
    """
    判断该行内容是否需要被过滤。
    包含黑名单关键词或@@的行会被过滤。
    """
    if not line or "@@" in line:
        return True
    return any(keyword in line for keyword in FILTER_KEYWORDS)

def extract_domain(line: str) -> str | None:
    """
    从规则行中提取有效域名。
    支持以下格式：
      - 'DOMAIN,domain'
      - 'DOMAIN-SUFFIX,domain'
      - '+.domain'
      - '*.domain'
      - '.domain'
      - 纯域名
    """
    line = clean_line(line.strip())
    if is_filtered_line(line):
        return None
    for prefix, offset in [
        ("DOMAIN,", 7),
        ("DOMAIN-SUFFIX,", 14),
        ("+.", 2),
        ("*.", 2),
        (".", 1),
        ("-DOMAIN,", 8),
        ("-DOMAIN-SUFFIX,", 15),
        ("-+.", 3),
        ("-*.", 3),
        ("-.", 2)
    ]:
        if line.startswith(prefix):
            return line[offset:]
    if "." in line:
        return line
    return None

def is_remove_end(domain: str) -> bool:
    """
    检查域名是否以黑名单后缀结尾。
    """
    return any(domain.endswith(suffix) for suffix in REMOVE_END)

def filter_parent_domains(domains: set[str]) -> set[str]:
    """
    只保留父域名，去除子域名。
    例如只保留 example.com，去除 a.example.com。
    """
    sorted_domains = sorted(domains, key=lambda d: d[::-1])
    result = []
    for domain in sorted_domains:
        if not result or not domain.endswith("." + result[-1]):
            result.append(domain)
    return set(result)

async def read_lines(file_path: str):
    """
    异步逐块读取文件内容，每块约10KB。
    """
    with open(file_path, "r", encoding="utf8") as f:
        while True:
            lines = f.readlines(10000)
            if not lines:
                break
            yield lines

def process_chunk(chunk: list[str]) -> set[str]:
    """
    处理一块文件内容，提取所有合规域名，去除黑名单后缀。
    """
    result = set()
    for line in chunk:
        domain = extract_domain(line)
        if domain and not is_remove_end(domain):
            result.add(domain)
    return result

async def main():
    """
    主流程：处理命令行参数，读取文件，提取、过滤域名并写回文件。
    """
    if len(sys.argv) < 2:
        print("请提供输入文件路径作为参数")
        return
    file_name = sys.argv[1]
    all_domains = set()
    async for chunk in read_lines(file_name):
        all_domains.update(process_chunk(chunk))
    filtered_domains = filter_parent_domains(all_domains)
    with open(file_name, "w", encoding="utf8") as f:
        for domain in sorted(filtered_domains):
            f.write(f"{domain}\n")
    print(f"处理完成，生成的规则总数为：{len(filtered_domains)}")

if __name__ == "__main__":
    # 脚本入口
    asyncio.run(main())
