import os
import shutil
import uuid
from tkinter.filedialog import askdirectory

def generate_unique_filename(folder_path, filename):
    while True:
        unique_filename = uuid.uuid4().hex[:8] + '_' + filename
        new_path = os.path.join(folder_path, unique_filename)
        if not os.path.exists(new_path):
            return unique_filename

caminho = askdirectory(title="Escolha uma pasta")

lista_arquivos = os.listdir(caminho)

locais = {
    'img': [".jfif", ".jpeg", ".JPG", ".png", ".jpg"],
    'arquivos': [".pdf", ".docx"],
    'audios e videos': [".mp3", ".mp4"],
    'zipados': [".zip", ".rar", ".7z"],
    'Executaveis': [".exe"]
}

for arquivo in lista_arquivos:
    nome, extensao = os.path.splitext(f'{caminho}/{arquivo}')
    for pasta in locais:
        if extensao in locais[pasta]:
            if not os.path.exists(f"{caminho}/{pasta}"):
                os.mkdir(f"{caminho}/{pasta}")
            new_path = os.path.join(f"{caminho}/{pasta}", arquivo)
            if os.path.exists(new_path):
                new_filename = generate_unique_filename(f"{caminho}/{pasta}", arquivo)
                new_path = os.path.join(f"{caminho}/{pasta}", new_filename)
            os.rename(f"{caminho}/{arquivo}", new_path)
