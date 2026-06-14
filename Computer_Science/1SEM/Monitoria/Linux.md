# Criando a distro

[](https://github.com/Dan1Ems/Linux-From-Scratch-1/blob/main/CODES.md#criando-a-distro)

**ATENÇÃO**: Utilize `make mrproper` para resetar o .config do arquivo caso algo dê errado.

### Instalação

[](https://github.com/Dan1Ems/Linux-From-Scratch-1/blob/main/CODES.md#instala%C3%A7%C3%A3o)

Para que possamos criar a nossa distro, é necessário a instalação de alguns pacotes essenciais. Eles forncem os recursos básicos para compilar do código, preparar imagens de sistema, instalar/configurar bootloaders e testar em VMs. Formando a cadeia completa de `build -> empacotamento -> boot -> teste`.

```
sudo apt update && sudo apt install -y build-essential libncurses-dev bison flex libssl-dev libelf-dev bc cpio wget xorriso grub-pc-bin grub-efi-amd64-bin grub-common mtools squashfs-tools qemu-system-x86 tar xz-utils  
```

Agora, temos que baixar o tarball (conjunto de ficheiros e diretórios num arquivo TAR) do código fonte do kernel Linux versão 6.1.60. Ele será necessário para a compilação, gerar o initramfs e construir a imagem do sistema.

```
sudo wget https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-6.1.60.tar.xz  
```

Descompacte o arquivo instalado:

```
sudo tar -xvf linux-6.1.60.tar.xz
```

Muda para o diretório do arquivo descompactado:

```
cd linux-6.1.60
```

Agora temos que fazer a configutação do kernel, mas não faremos isso na mão. Vamos utilizar um comando que gera um arquivo de configuração padrão, é muito prático para que não escreva em torno de 15 mil variáveis.

```
sudo make defconfig
```

Entretanto, o arquivo de configurção padrão vem com algumas opções desativadas. Elas são importantes para a comunicação do entre kernel, CPU e disco ser possível. Nesse caso, eu utilizarei o `nvim` para editar a configuração, mas você pode utilizar qualquer editor de texto.

```
sudo nvim .config
```

No arquivo .config procure pelas opções de configuração descritas abaixo. Para facilitar, utilize o mecanismo de busca do seu editor de texto.

Caso alguns dos módulos não estejam como YES na sua configuração, altere manualmente seguindo o formato padrão do arquivo.

```
// EXEMPLO

# CONFIG_BLK_DEV_NVME is not set -> CONFIG_BLK_DEV_NVME=y
```

```
CONFIG_BINFMT_ELF=y
CONFIG_EXT4_FS=y
CONFIG_BLK_DEV=y
CONFIG_SCSI=y
CONFIG_SATA_AHCI=y
CONFIG_BLK_DEV_NVME=y
CONFIG_PROC_FS=y
```

Agora precisamos garantir que os módulos que precisaremos estarão carregados, desativando opções do kernel que não serão necessárias e mantem as opções de dirvers utilizados pelo sistema atual, perguntando interativamente sobre os itens opcionais. Para verificar isso vamos rodar o comandos a seguir.

```
sudo make localmodconfig # Aperte Yes para tudo
```

**REFAZER DAQUI**

Gera imagem + móulos:

```
sudo make -j$(nproc)
```

Volta para a home:

```
cd $HOME
```

Faz o download o BusyBox:

```
sudo wget https://busybox.net/downloads/busybox-1.37.0.tar.bz2
```

Descompactando o arquivo instalado:

```
tar -xvf busybox-1.37.0.tar.bz2
```

Muda para o diretório do arquivo descompactado

```
cd busybox-1.37.0
```

Cria o arquivo de configuração:

```
sudo make defconfig
```

É necessario que o BusyBox esteja no modo estático, para isso, vamos verificar no arquivo de configuração:

```
cat .config | grep "STATIC"
```

Deve aparecer algo como:

```
# CONFIG_STATIC is not set
# CONFIG_FEATURE_LIBBUSYBOX_STATIC is not set
CONFIG_STATIC_LIBGCC=y
```

Nesse caso, é necessário alterar o CONFIG_STATIC dento do arquivo .config:

```
sed 's/# CONFIG_STATIC is not set/CONFIG_STATIC=y/' .config
```

Troque também o CONFIG_TC no arquivo .config:

```
sed 's/CONFIG_TC/# CONFIG_TC is not set/' .config
```

Instale o musl:

```
sudo apt install -d musl
```

Faça a compilação:

```
sudo make -j$(nproc)
```

Volta para a home:

```
cd $HOME
```

Cria o diretório initramfs (carregar o file system na ram):

```
mkdir initramfs; cd initramfs; mkdir bin proc sys dev mnt
```

Copia o BusyBox para o bin do novo diretório:

```
cp busybox-1.37.0/busybox initramfs/bin
```

Vá para o diretório bin:

```
cd initramfs/bin
```

Dá a devida permissão para o executável copiado:

```
chmod +755 busybox
```

Crie um arquivo de script:

```
touch script.sh
```

Dentro do arquivo script.sh, coloque:

```
#!/bin/bash

for programa in $(./busybox --list); do
        ln -s busybox ./$programa
done
```

Dê permissão para o arquivo script.sh:

```
chmod +755 script.sh
```

Execute o script:

```
./script.sh
```

Volte para o arquivo initramfs:

```
cd ..
```

Crie um arquivo init:

```
touch init
```

Dentro do arquivo init, coloque:

```
#!/bin/sh

mount -t proc none /proc
mount -t sysfs none /sys
mount -t devtmpfs none /dev

echo "Inicializando a disto..."
```

Dê a permissão para o arquivo init:

```
chmod +755 init
```