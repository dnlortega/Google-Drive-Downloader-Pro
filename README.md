# Google Drive Downloader Pro 🚀

Uma ferramenta robusta, profissional e autônoma para baixar arquivos em massa e diretórios públicos do Google Drive, otimizada para máxima velocidade, resiliência e conveniência do usuário.

## 🌟 Principais Funcionalidades

- **🚀 Multithreading (Modo Turbo):** Baixe até 10 arquivos simultaneamente. Configurável dinamicamente através de um controle deslizante na aba de configurações.
- **🗂️ Filtros Inteligentes:** Escolha baixar toda a pasta ou filtre automaticamente para baixar apenas *Imagens*, *Vídeos* ou *Documentos*. O sistema ignora o restante.
- **🔀 Ordenação Flexível:** Ordene a fila de downloads por ordem alfabética (**Nome A-Z** ou **Nome Z-A**) ou mantenha o **Padrão do Drive** original.
- **🛡️ Rede Resiliente (Auto-Retry):** Em caso de falhas de rede, queda de energia na placa de wifi ou instabilidade do servidor, o sistema tenta reconectar e baixar o arquivo novamente (até 3 tentativas invisíveis) antes de acusar falha.
- **⏩ Eficiência de Banda:** O sistema identifica se um arquivo da nuvem já existe localmente na pasta de destino e o pula automaticamente (Skip), economizando tempo e uso da internet.
- **📂 Interface Dinâmica com Abas em Tempo Real:**
  - **Fila de Download:** Veja o progresso (velocidade individual em MB/s e porcentagem) de cada arquivo ativo. O arquivo que está sendo baixado no momento recebe um forte destaque azul em negrito na UI.
  - **Concluídos:** Assim que um download termina ou é pulado, ele migra instantânea e automaticamente para a aba de concluídos, mantendo a fila sempre limpa.
- **📊 Relatório Final TXT:** Ao término, gera um relatório detalhado na pasta destino contendo os logs exatos de tudo que obteve Sucesso, Falha, Cancelamento ou foi Pulado, com data e hora.
- **🔔 Alertas Nativos:** Integração com o sistema do Windows. Ao concluir os downloads, um "Toast" (alerta nativo com som) surge no canto da tela informando a conclusão.
- **📜 Histórico Inteligente:** A ferramenta lembra os últimos 5 links pesquisados e os salva automaticamente na memória (através de um arquivo JSON local), criando um prático menu suspenso (ComboBox).
- **🧹 Ferramenta de Limpeza:** Um botão vermelho dedicado para limpar todo o conteúdo da pasta de destino com um clique (inclui barreira de segurança e pop-up de confirmação).
- **🌗 Personalização de Tema:** Suporte para alternar entre **Modo Claro** e **Modo Escuro** em tempo real através do painel de Opções (⚙️).

## 📦 Como Usar (Versão Executável / Standalone)

Não é necessário instalar Python, dependências ou usar o terminal!
1. Vá até a pasta `dist/` e abra o arquivo `app.exe`.
2. Clique no botão **Procurar Pasta** para escolher em qual diretório ou HD você deseja salvar os arquivos.
3. Cole o link público da pasta do Google Drive.
4. Escolha seus **Filtros** ou preferências de **Ordenação**.
5. Clique em **Analisar**.
6. Revise a fila e clique no botão verde **Iniciar Download**.

## 💻 Como Usar (Via Código-Fonte)

Caso deseje rodar a aplicação via terminal e alterar o código:
1. Instale as bibliotecas base:
   ```bash
   pip install customtkinter gdown plyer pyinstaller
   ```
2. Execute o arquivo principal:
   ```bash
   python app.py
   ```
3. Se desejar recompilar o sistema para atualizar o `.exe` após realizar alterações no código:
   ```bash
   python -m PyInstaller --noconsole --onefile app.py
   ```
