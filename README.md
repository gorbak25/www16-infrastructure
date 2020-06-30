So i don't forget:
```
Match user www16
#	ChrootDirectory %h
	X11Forwarding no
	AllowTcpForwarding no
	PasswordAuthentication yes
	AllowAgentForwarding no
	GatewayPorts no
	Banner /home/www16/ssh_banner
	ForceCommand sudo --preserve-env=SSH_ORIGINAL_COMMAND /home/www16/www16-infrastructure/ssh_entry.py
```

and:
```
www16 ALL = (root) NOPASSWD: /home/www16/www16-infrastructure/ssh_entry.py
Defaults env_keep += "SSH_ORIGINAL_COMMAND"
```
