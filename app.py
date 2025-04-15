from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
import os
import shutil
from werkzeug.utils import secure_filename
from datetime import datetime
import logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'  # Mude para uma chave segura em produção

# Configurações
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limite de 16MB

# Verificar se o arquivo tem extensão
def allowed_file(filename):
    return '.' in filename

# Adicionar filtro datetime
@app.template_filter('datetime')
def format_datetime(value, format="%d/%m/%Y %H:%M"):
    if value is None:
        return ""
    return datetime.fromtimestamp(value).strftime(format)

# Rota principal - Listagem de arquivos
@app.route('/')
@app.route('/<path:folder_path>')
def index(folder_path=''):
    base_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_path)
    
    if not os.path.exists(base_path):
        return redirect(url_for('index'))
    
    # Breadcrumbs
    breadcrumbs = []
    parts = folder_path.split('/') if folder_path else []
    for i in range(len(parts)):
        breadcrumbs.append({
            'name': parts[i],
            'path': '/'.join(parts[:i+1])
        })
    
    # Listar arquivos e pastas
    items = os.listdir(base_path)
    files = []
    folders = []
    
    for item in items:
        full_path = os.path.join(base_path, item)
        if os.path.isfile(full_path):
            files.append({
                'name': item,
                'path': folder_path,
                'size': f"{os.path.getsize(full_path) / 1024:.2f} KB",
                'modified': os.path.getmtime(full_path),
                'is_root': not bool(folder_path)
            })
        else:
            try:
                # Contagem segura de arquivos
                sub_items = os.listdir(full_path)
                file_count = len([f for f in sub_items if os.path.isfile(os.path.join(full_path, f))])
            except Exception:
                file_count = 0  # Fallback seguro
                
            folders.append({
                'name': item,
                'path': os.path.join(folder_path, item) if folder_path else item,
                'file_count': file_count
            })
    
    # Listar todas as pastas para o menu de movimentação
    all_folders = []
    for root, dirs, _ in os.walk(app.config['UPLOAD_FOLDER']):
        for dir_name in dirs:
            rel_path = os.path.relpath(os.path.join(root, dir_name), app.config['UPLOAD_FOLDER'])
            all_folders.append({
                'name': dir_name,
                'path': rel_path if rel_path != '.' else ''
            })
    
    return render_template('file_list.html', 
                         files=files, 
                         folders=folders,
                         all_folders=all_folders,
                         breadcrumbs=breadcrumbs,
                         current_path=folder_path)

# Rota de upload modificada
@app.route('/upload', methods=['POST'])
def upload_file():
    current_path = request.form.get('current_path', '')
    uploaded_files = request.files.getlist('file')
    
    for file in uploaded_files:
        if file.filename:
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], current_path, filename)
            file.save(save_path)
    
    return redirect(url_for('index', folder_path=current_path))

# Nova rota para mover arquivos
@app.route('/move_files', methods=['POST'])
def move_files():
    current_path = request.form.get('current_path', '')
    target_folder = request.form.get('target_folder', '')
    file_names = request.form.getlist('file_names')
    
    for file_name in file_names:
        src = os.path.join(app.config['UPLOAD_FOLDER'], current_path, file_name)
        dst = os.path.join(app.config['UPLOAD_FOLDER'], target_folder, file_name)
        try:
            shutil.move(src, dst)
        except Exception as e:
            flash(f'Erro ao mover {file_name}: {str(e)}')
    
    return redirect(url_for('index', folder_path=current_path))

# Rota de download com logs
@app.route('/download/<path:filepath>')
def download(filepath):
    try:
        if filepath.startswith('root/'):
            filepath = filepath[5:]
        directory = os.path.join(app.config['UPLOAD_FOLDER'], os.path.dirname(filepath))
        return send_from_directory(
            directory=directory,
            path=os.path.basename(filepath),
            as_attachment=True
        )
    except Exception as e:
        flash(f'Erro ao baixar arquivo: {str(e)}')
        return redirect(url_for('index'))

# Rota para excluir arquivo
@app.route('/delete/<path:filepath>')
def delete(filepath):
    try:
        if filepath.startswith('root/'):
            filepath = filepath[5:]
        full_path = os.path.join(app.config['UPLOAD_FOLDER'], filepath)
        if os.path.exists(full_path):
            os.remove(full_path)
            flash('Arquivo excluído com sucesso!')
    except Exception as e:
        flash(f'Erro ao excluir: {str(e)}')
    return redirect(url_for('index'))

# Rota para gerenciamento de pastas
@app.route('/folder_action', methods=['POST'])
def folder_action():
    action = request.form.get('action')
    folder_name = request.form.get('folder_name')
    new_name = request.form.get('new_name', '')
    current_path = request.form.get('current_path', '')
    
    try:
        base_path = os.path.join(app.config['UPLOAD_FOLDER'], current_path)
        
        if action == 'create' and folder_name:
            os.makedirs(os.path.join(base_path, folder_name), exist_ok=True)
            flash(f'Pasta "{folder_name}" criada!')
            
        elif action == 'rename' and folder_name and new_name:
            os.rename(
                os.path.join(base_path, folder_name),
                os.path.join(base_path, new_name)
            )
            flash(f'Pasta renomeada para "{new_name}"!')
            
        elif action == 'delete' and folder_name:
            shutil.rmtree(os.path.join(base_path, folder_name))
            flash(f'Pasta "{folder_name}" excluída!')
            
    except Exception as e:
        flash(f'Erro: {str(e)}')
    
    return redirect(url_for('index', folder_path=current_path))

# Configuração para produção
if __name__ == '__main__':
    # Em desenvolvimento
    app.run(debug=True)
    
    # Em produção, usar:
    # app.run(host='0.0.0.0', port=5000)
