import olefile, re

path = r"F:\eduClaw\doc\报告\开发与应用报告.doc"
ole = olefile.OleFileIO(path)

# Try to find the Word Document stream
streams = ole.listdir()
for s in streams:
    print(f"Stream: {'/'.join(s)}")

# Try reading WordDocument stream
if ole.exists("WordDocument"):
    data = ole.openstream("WordDocument").read()

# Try reading 1Table or 0Table
for table_name in ["1Table", "0Table"]:
    if ole.exists(table_name):
        print(f"Found {table_name}")

# Try extracting text from all streams
for stream_path in streams:
    stream_name = "/".join(stream_path)
    try:
        data = ole.openstream(stream_path).read()
        # Check for Chinese text
        text = data.decode('utf-16-le', errors='ignore')
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        if chinese_chars > 20:
            print(f"\n--- {stream_name} ({chinese_chars} chinese chars) ---")
            # Clean up the text
            clean = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
            print(clean[:2000])
    except:
        pass

ole.close()