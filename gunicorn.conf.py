# Configuração do Gunicorn para produção no Render
bind    = "0.0.0.0:10000"   # porta que o Render espera
workers = 2                  # processos paralelos
threads = 2                  # threads por processo
timeout = 120                # segundos antes de matar um worker travado