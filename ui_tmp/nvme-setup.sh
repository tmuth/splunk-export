#!/bin/sh

mdadm --create --verbose --auto=yes /dev/md0 --level=0 --raid-devices=2 /dev/nvme0n1 /dev/nvme1n1
mkfs.ext4  /dev/md0
mkdir -p /mnt/nvme
mount /dev/md0 /mnt/nvme
