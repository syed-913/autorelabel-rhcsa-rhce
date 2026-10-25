# Builds the autorelabel/rhel10 Vagrant box offline from the RHEL 10 DVD ISO.
# No registration, no subscription. Driven by `./autorelabel box build`.

packer {
  required_plugins {
    qemu = {
      version = "~> 1.1"
      source  = "github.com/hashicorp/qemu"
    }
    virtualbox = {
      version = "~> 1.1"
      source  = "github.com/hashicorp/virtualbox"
    }
    vagrant = {
      version = "~> 1.1"
      source  = "github.com/hashicorp/vagrant"
    }
  }
}

variable "iso_path" {
  type = string
}

variable "iso_checksum" {
  type    = string
  default = "none"
}

variable "output_dir" {
  type = string
}

variable "box_version" {
  type    = string
  default = "0"
}

variable "volume_label" {
  type    = string
  default = "RHEL-10-0-BaseOS-x86_64"
}

variable "cpus" {
  type    = number
  default = 2
}

variable "memory" {
  type    = number
  default = 2048
}

locals {
  vagrant_keys = join("\n", [
    file("${path.root}/keys/vagrant.pub.ed25519"),
    file("${path.root}/keys/vagrant.pub.rsa"),
  ])
  kickstart = templatefile("${path.root}/http/ks.cfg.pkrtpl", {
    vagrant_keys = local.vagrant_keys
  })
  boot_command = [
    "<up><wait>",
    "e<wait>",
    "<down><down><end><wait>",
    " inst.text inst.ks=http://{{ .HTTPIP }}:{{ .HTTPPort }}/ks.cfg",
    "<wait><leftCtrlOn>x<leftCtrlOff>",
  ]
}

source "qemu" "rhel10" {
  iso_url          = var.iso_path
  iso_checksum     = var.iso_checksum
  output_directory = "${var.output_dir}/qemu"
  vm_name          = "box.img"
  format           = "qcow2"
  disk_size        = "20G"
  disk_interface   = "virtio"
  disk_discard     = "unmap"
  disk_compression = true
  net_device       = "virtio-net"
  accelerator      = "kvm"
  cpu_model        = "host"
  cpus             = var.cpus
  memory           = var.memory
  headless         = true
  vnc_bind_address = "127.0.0.1"
  http_content     = { "/ks.cfg" = local.kickstart }
  boot_wait        = "6s"
  boot_command     = local.boot_command
  ssh_username     = "vagrant"
  ssh_password     = "vagrant"
  ssh_timeout      = "90m"
  shutdown_command = "sudo /usr/sbin/shutdown -P now"
  qemuargs = [
    ["-serial", "file:${var.output_dir}/qemu-serial.log"],
  ]
}

source "virtualbox-iso" "rhel10" {
  iso_url                  = var.iso_path
  iso_checksum             = var.iso_checksum
  output_directory         = "${var.output_dir}/virtualbox"
  vm_name                  = "autorelabel-build-rhel10"
  guest_os_type            = "RedHat_64"
  disk_size                = 20480
  hard_drive_interface     = "sata"
  # No discard (TRIM): VirtualBox 7.2's SATA controller can hang for good on a discard request.
  # A build froze in fstrim and could not even power off ("1 async tasks - ahci/0"), and the lab
  # VMs inherit this setting, where RHEL's weekly fstrim.timer could freeze a node mid-exam.
  hard_drive_discard       = false
  cpus                     = var.cpus
  memory                   = var.memory
  headless                 = true
  guest_additions_mode     = "disable"
  http_content             = { "/ks.cfg" = local.kickstart }
  boot_wait                = "6s"
  boot_command             = local.boot_command
  ssh_username             = "vagrant"
  ssh_password             = "vagrant"
  ssh_timeout              = "90m"
  shutdown_command         = "sudo /usr/sbin/shutdown -P now"
  vboxmanage = [
    ["modifyvm", "{{ .Name }}", "--nat-localhostreachable1", "on"],
    # Not KVM's paravirtual clock: it at random stalls the boot right after the boot loader.
    ["modifyvm", "{{ .Name }}", "--paravirt-provider", "minimal"],
    ["modifyvm", "{{ .Name }}", "--uart1", "0x3F8", "4", "--uartmode1", "file", "${var.output_dir}/vbox-serial.log"],
  ]
}

build {
  sources = ["source.qemu.rhel10", "source.virtualbox-iso.rhel10"]

  provisioner "shell" {
    execute_command = "sudo -E bash '{{ .Path }}'"
    scripts = [
      "${path.root}/scripts/base.sh",
      "${path.root}/scripts/cleanup.sh",
    ]
  }

  post-processor "vagrant" {
    output               = "${var.output_dir}/autorelabel-rhel10-{{ .Provider }}.box"
    compression_level    = 6
    vagrantfile_template = "${path.root}/box-Vagrantfile"
  }
}
