import os
import pathlib
from flask import Flask, render_template, request, jsonify
import pathspec

app = Flask(__name__)

def get_gitignore_spec(dir_path):
    """Reads the .gitignore file and returns a pathspec object."""
    gitignore_path = os.path.join(dir_path, '.gitignore')
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            return pathspec.PathSpec.from_lines('gitwildmatch', f)
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cover_letter')
def cover_letter():
    return render_template('cover_letter.html')

@app.route('/scan', methods=['POST'])
def scan_dir():
    data = request.json
    dir_path = data.get('path', '').strip()
    use_gitignore = data.get('use_gitignore', True)

    path = pathlib.Path(dir_path)
    if not path.is_dir():
        return jsonify({'error': f'Invalid directory path: {dir_path}'})

    spec = get_gitignore_spec(dir_path) if use_gitignore else None
    
    file_list = []
    try:
        for root, dirs, files in os.walk(dir_path):
            # Skip hidden git directories immediately to save time
            if '.git' in dirs:
                dirs.remove('.git')
                
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, dir_path)
                
                is_ignored = False
                if spec and spec.match_file(rel_path):
                    is_ignored = True
                    
                # Standard Python exclusions just to be safe
                if '.venv' in rel_path or '__pycache__' in rel_path:
                    is_ignored = True

                # --- NEW LOGIC: Skip the file entirely if it's ignored ---
                if is_ignored:
                    continue

                file_list.append({
                    'path': rel_path
                })
                
        # Sort alphabetically so folders group together nicely
        file_list.sort(key=lambda x: x['path'])
        
    except Exception as e:
        return jsonify({'error': str(e)})

    return jsonify({'files': file_list})


@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    files = data.get('files', [])
    prompt_text = data.get('prompt', '')
    base_path = data.get('base_path', '')

    # Start with the prompt
    result = prompt_text + "\n\n" if prompt_text else ""

    for rel_path in files:
        full_path = os.path.join(base_path, rel_path)
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            result += f"--- Content of {rel_path} ---\n{content}\n\n"
        except Exception as e:
            result += f"--- Error reading {rel_path}: {e} ---\n\n"

    return jsonify({'result': result})

if __name__ == '__main__':
    # Runs locally on port 5000
    app.run(debug=True)