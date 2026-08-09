import os
import pytest
from downloader import DownloaderCore, SingleFile

def test_filtro_imagens():
    core = DownloaderCore({})
    
    arquivos = [
        SingleFile("1", "foto1.jpg"),
        SingleFile("2", "doc.pdf"),
        SingleFile("3", "video.mp4"),
        SingleFile("4", "image.png")
    ]
    
    filtrados = core._filtrar_arquivos(arquivos, "Imagens")
    assert len(filtrados) == 2
    assert filtrados[0].id == "1"
    assert filtrados[1].id == "4"

def test_filtro_videos():
    core = DownloaderCore({})
    
    arquivos = [
        SingleFile("1", "video1.mkv"),
        SingleFile("2", "doc.pdf"),
        SingleFile("3", "video2.mp4"),
    ]
    
    filtrados = core._filtrar_arquivos(arquivos, "Vídeos")
    assert len(filtrados) == 2
    assert filtrados[0].id == "1"
    assert filtrados[1].id == "3"

def test_filtro_documentos():
    core = DownloaderCore({})
    
    arquivos = [
        SingleFile("1", "planilha.xlsx"),
        SingleFile("2", "doc.pdf"),
        SingleFile("3", "video2.mp4"),
    ]
    
    filtrados = core._filtrar_arquivos(arquivos, "Documentos")
    assert len(filtrados) == 2
    assert "xlsx" in filtrados[0].local_path
    assert "pdf" in filtrados[1].local_path

def test_filtro_todos():
    core = DownloaderCore({})
    arquivos = [SingleFile("1", "a.txt"), SingleFile("2", "b.jpg")]
    filtrados = core._filtrar_arquivos(arquivos, "Todos")
    assert len(filtrados) == 2
