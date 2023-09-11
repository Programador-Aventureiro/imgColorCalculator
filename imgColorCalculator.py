# Importação de bibliotecas necessárias
import cv2
import numpy as np
import os
import re
import glob
import shutil
import flet as ft
import flet
from flet import (
    ElevatedButton,
    FilePicker,
    FilePickerResultEvent,
    Page,
    Row,
    Text,
    icons,
)

# Obtendo o diretório atual do script
DIR = os.path.dirname(os.path.abspath(__file__))

# Função para verificar se a cor está em formato HEX válido
def is_hex_format(hex_color: str) -> bool:
    # Padrão regex para uma cor HEX válida
    padrao = re.compile(r'^#([A-Fa-f0-9]{6})$')

    # Verifica se a cor corresponde ao padrão
    if padrao.match(hex_color):
        return True
    else:
        return False

# Função para converter uma cor HEX em formato BGR
def hex_para_bgr(cor_hex) -> str:
    # Use regex para manter apenas os dígitos hexadecimais
    numeros_hex = re.sub('[^0-9a-fA-F]', '', cor_hex)

    # Preencha com zeros à esquerda se necessário (para garantir 6 dígitos)
    numeros_hex = numeros_hex.zfill(6)

    # Converta o valor HEX para inteiros
    valor_inteiro = int(numeros_hex, 16)

    # Extraia os componentes de cor BGR
    azul = (valor_inteiro >> 16) & 255
    verde = (valor_inteiro >> 8) & 255
    vermelho = valor_inteiro & 255

    return (azul, verde, vermelho)

# Função para escanear a cor em uma imagem
def color_scan(img: str, target_color: str) -> None:
    # Carregue a imagem
    imagem = cv2.imread(img)

    # Defina a cor que você deseja identificar (no formato BGR)
    cor_alvo = hex_para_bgr(target_color)
    cor_alvo = np.array(cor_alvo, dtype=np.uint8)

    # Calcule a diferença entre a cor alvo e cada pixel na imagem
    diferenca = np.abs(imagem - cor_alvo)

    # Converta a imagem de diferença para escala de cinza
    diferenca_cinza = cv2.cvtColor(diferenca, cv2.COLOR_BGR2GRAY)

    # Defina um limite para identificar áreas onde a cor alvo está presente
    limite = 50  # Você pode ajustar esse valor conforme necessário

    # Encontre os pixels que correspondem à cor alvo
    pixels_cor_alvo = np.where(diferenca_cinza <= limite)

    # Calcule a porcentagem de incidência da cor alvo na imagem
    total_pixels = imagem.shape[0] * imagem.shape[1]
    porcentagem_incidencia = (len(pixels_cor_alvo[0]) / total_pixels) * 100

    return {'imagem': img, 'porcentagem_incidencia': porcentagem_incidencia, 'diferenca_cinza': diferenca_cinza}

# Função principal que define a interface do aplicativo
def main(page: Page):
    # Configurações da página
    page.bgcolor = ft.colors.WHITE
    page.title = 'Organizador de imagens'
    page.padding = 0
    page.window_width = 500
    page.window_height = 750
    page.window_resizable = False

    # Definindo os botões para selecionar diretórios de entrada e saída
    def get_directory_result(e: FilePickerResultEvent):
        directory_path.value = e.path if e.path else ""
        directory_path.update()

    get_directory_dialog = FilePicker(on_result=get_directory_result)

    def get_directory_output(e: FilePickerResultEvent):
        directory_output.value = e.path if e.path else ""
        directory_output.update()

    get_directory_dialog_for_output = FilePicker(on_result=get_directory_output)

    directory_path = Text(size=10, color=ft.colors.BLACK)
    directory_output = Text(size=10, color=ft.colors.BLACK)

    # Oculta todos os diálogos no overlay
    page.overlay.extend([get_directory_dialog, get_directory_dialog_for_output])

    # Interface para selecionar o diretório de entrada
    get_input_folder = ft.Column(
        controls = [
            Text(
                value='Selecione o diretório das imagens a serem analisadas', 
                size=20, 
                weight=ft.FontWeight.W_900,
                color=ft.colors.BLACK,
            ),
            ElevatedButton(
                "Escolher diretório",
                icon=icons.FOLDER_OPEN,
                on_click=lambda _: get_directory_dialog.get_directory_path(),
                disabled=page.web,
            ),
            directory_path,
        ]
    )

    # Interface para selecionar o diretório de saída
    get_output_folder = ft.Column(
        controls = [
            Text(
                value='Selecione o diretório de saída onde as imagens serão copiadas', 
                size=20, 
                weight=ft.FontWeight.W_900,
                color=ft.colors.BLACK,
            ),
            ElevatedButton(
                "Escolher diretório",
                icon=icons.FOLDER_OPEN,
                on_click=lambda _: get_directory_dialog_for_output.get_directory_path(),
                disabled=page.web,
            ),
            directory_output,
        ]
    )

    # Campo de entrada para inserir a cor em formato HEX
    hex_color = ft.TextField(
        label="Digite uma cor no formato HEX", 
        hint_text="Exemplo #FFF000",
        bgcolor=ft.colors.WHITE,
        color=ft.colors.BLACK
    )

    # Campo de mensagem para exibir informações ao usuário
    message = Text(size=10, weight=ft.FontWeight.W_900, color=ft.colors.BLACK)
    
    # Tabela para exibir os resultados da análise
    data_output = ft.DataTable(heading_row_color=ft.colors.GREY_700, data_row_color=ft.colors.WHITE)

    # Função para validar e iniciar a análise
    def validate():
        nonlocal message

        # Verifique se os diretórios de entrada e saída foram selecionados
        if not directory_path.value:
            message.value = 'O diretório de entrada não foi selecionado!'
            message.update()
            return

        if not directory_output.value:
            message.value = 'O diretório de saída não foi selecionado!'
            message.update()
            return

        # Verifique se uma cor em formato HEX foi fornecida
        if not hex_color.value:
            message.value = 'Não foi fornecido uma cor no formato HEX (Ex: #FFF000)'
            message.update()
            return

        # Verifique se a cor fornecida está em formato HEX válido
        if not is_hex_format(hex_color.value):
            message.value = 'A cor não está no formato HEX (Ex: #FFF000)'
            message.update()
            return
        
        # Inicie a análise das imagens
        message.value = 'Analisando as imagens'
        message.update()

        # Tipos de arquivos de imagem suportados
        supported_files = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']

        # Encontre todos os arquivos de imagem no diretório de entrada
        files = []
        for sp in supported_files:
            files += glob.glob(os.path.join(directory_path.value, f'*{sp}'))

        output = []
        for file in files:
            result = color_scan(file, hex_color.value.upper())
            output.append(result)

        if output:
            # Ordene os resultados por porcentagem de incidência da cor
            output = sorted(output, key=lambda x: x['porcentagem_incidencia'], reverse=True)[:100]

            # Configuração das colunas da tabela de saída
            data_output.columns = [
                ft.DataColumn(ft.Text("Imagem", color=ft.colors.WHITE)),
                ft.DataColumn(ft.Text("% incidência", color=ft.colors.WHITE)),
            ]

            # Preenchimento das linhas da tabela de saída
            data_output.rows = [
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(os.path.basename(o["imagem"])[:30], color=ft.colors.BLACK)),
                        ft.DataCell(ft.Text(f'{o["porcentagem_incidencia"]:.2f}%', color=ft.colors.BLACK)),
                    ],
                ) for o in output]

            data_output.update()

            # Copie os arquivos de imagem com a cor predominante para o diretório de saída
            for num, o in enumerate(output):
                source = o["imagem"]
                ext = os.path.splitext(source)[-1]
                destiny = os.path.join(directory_output.value, str(num) + ext)
                shutil.copy2(source, destiny)
            
            message.value = f'{len(output)} arquivos copiados'
            message.update()

    # Botão para iniciar a análise
    action = ft.ElevatedButton(
        text='Analisar', 
        icon=ft.icons.SETTINGS_SHARP,
        on_click=lambda _: validate(), 
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=20,
        )
    )

    # Container principal que contém todos os elementos da interface
    content = ft.Container(
        content=ft.Column(
            controls=[get_input_folder, get_output_folder, hex_color, action, message, data_output], 
            alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=True,
        ),
        alignment=ft.alignment.top_center,
        width=page.window_width,
        height=page.window_height,
        image_src=os.path.join(DIR, 'background.jpg'),
        image_opacity=0.8,
        padding=20,
        image_fit=ft.ImageFit.COVER
    )

    # Adicione o conteúdo à página
    page.add(content)

# Iniciar o aplicativo
flet.app(target=main)
