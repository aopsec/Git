#!/bin/bash
clear 
sudo apt update && sudo apt upgrade -y 
sudo apt install micro -y
sudo apt install tor -y
sudo apt install torbrowser-launcher -y
sudo apt install -y iptables macchanger dnsutils curl tcpdump net-tools
echo "net.ipv6.conf.all.disable_ipv6 = 1" >> /etc/sysctl.conf

# Config Tor
echo "SocksPort 9050" >> /etc/tor/torrc
echo "ControlPort 9051" >> /etc/tor/torrc
echo "CookieAuthentication 1" >> /etc/tor/torrc
echo "RunAsDaemon 1" >> /etc/tor/torrc
echo "DataDirectory /var/lib/tor" >> /etc/tor/torrc
echo "Log notice file /var/log/tor/notices.log" >> /etc/tor/torrc
echo "Log debug file /var/log/tor/debug.log" >> /etc/tor/torrc

# Reiniciar Tor 
sudo systemctl restart tor
sudo systemctl enable tor
sudo systemctl start tor

# Desabilitar IPv6 
echo "net.ipv6.conf.all.disable_ipv6 = 1" >> /etc/sysctl.conf

# Configurar wget para usar Tor
echo "use_proxy = on" >> ~/.wgetrc
echo "http_proxy = 127.0.0.1:9050" >> ~/.wgetrc
echo "https_proxy = 127.0.0.1:9050" >> ~/.wgetrc

# Mullvad Install
sudo curl -fsSLo /usr/share/keyrings/mullvad-keyring.asc https://repository.mullvad.net/deb/mullvad-keyring.asc
echo "deb [signed-by=/usr/share/keyrings/mullvad-keyring.asc arch=$( dpkg --print-architecture )] https://repository.mullvad.net/deb/stable stable main" | sudo tee /etc/apt/sources.list.d/mullvad.list
sudo apt update && sudo apt install mullvad-vpn

# git config
git config --global user.name "Advan7Sapo"
git config --global user.email "aops@outlook.com.br"

#-----------------------------------------------------------------------------------
sudo systemctl status tor 

echo "IniT.sh completed successfully!"
