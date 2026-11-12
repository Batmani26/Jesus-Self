import os
import html
import webbrowser

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>کدهای سلف‌بات من</title>
    <style>
        body { font-family: Tahoma, sans-serif; background: #1e1e1e; color: #d4d4d4; margin: 0; display: flex; }
        #sidebar { width: 300px; background: #252526; padding: 20px; border-left: 1px solid #333; overflow-y: auto; height: 100vh; }
        #content { flex: 1; padding: 20px; overflow-y: auto; height: 100vh; }
        h1, h2 { color: #4ec9b0; }
        ul { list-style: none; padding: 0; }
        li { margin: 10px 0; }
        a { color: #569cd6; text-decoration: none; cursor: pointer; display: block; padding: 5px; border-radius: 4px; }
        a:hover { background: #2a2d2e; }
        pre { background: #1e1e1e; padding: 15px; border-radius: 5px; border: 1px solid #333; direction: ltr; text-align: left; overflow-x: auto; font-family: Consolas, monospace; }
        .folder { color: #dcb67a; font-weight: bold; margin-top: 15px; }
    </style>
</head>
<body>
    <div id="sidebar">
        <h1>📁 فایل‌های پروژه</h1>
        <ul>
            {files_html}
        </ul>
    </div>
    <div id="content">
        <h2>👈 روی یکی از فایل‌های سمت راست کلیک کن</h2>
        <p>اینجا کد کامل نمایش داده می‌شه.</p>
    </div>
    <script>
        const files = {files_json};
        function showFile(name) {
            document.getElementById('content').innerHTML = '<h2>📄 ' + name + '</h2><pre>' + files[name] + '</pre>';
        }
    </script>
</body>
</html>
"""

def main():
    files_list = []
    files_json = {}

    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git')]
        for file in files:
            if file.endswith(('.py', '.txt', '.md', '.example')):
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, BASE_DIR)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # escape for JS injection safely
                        content_escaped = html.escape(content).replace("'", "\\'").replace('\n', '\\n')
                        files_json[rel_path] = content_escaped
                        files_list.append(f'<li><a onclick="showFile(\'{rel_path}\')">📄 {rel_path}</a></li>')
                except Exception as e:
                    print(f'Error reading {filepath}: {e}')

    files_html = "\n".join(files_list)
    json_str = "{"
    for k, v in files_json.items():
        json_str += f"'{k}': '{v}',"
    json_str += "}"

    html_content = HTML_TEMPLATE.replace('{files_html}', files_html).replace('{files_json}', json_str)

    out_path = os.path.join(BASE_DIR, 'view_code.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f'File created: {out_path}')
    print('Opening in browser...')
    webbrowser.open('file://' + out_path)

if __name__ == '__main__':
    main()
