import os 
from tkinter.filedialog import askdirectory

caminho = askdirectory(title="Escolha uma pasta")

lista_arquivos = os.listdir(caminho)

locais = {
    'img': [".jfif", ".jpeg" ,".JPG", ".png"],
    'pdfs': [".pdf"],
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
      os.rename(f"{caminho}/{arquivo}", f"{caminho}/{pasta}/{arquivo}")