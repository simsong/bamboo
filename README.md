# Bamboo DVR
Bamboom DVR is a smart digital video archiving and analysis platform.

## Goals
* Archive our Google Nest cameras

## Other Comparisons
In creating BambooDVR, we considered:

|Product|Description|Tech|
|---|---|---|
|[Frigate]([url](https://frigate.video)https://frigate.video)|Open Source DVR system|Python and Docker|

sudo apt-get install build-essential yasm cmake libtool libc6 libc6-dev unzip wget libnuma1 libnuma-dev
apt install ninja-build
sudo apt install python3-devel




# install ffmpeg with H.265 installed

You need to add the rpmfusion repos:

sudo dnf install https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm && sudo dnf groupupdate multimedia --setop="install_weak_deps=False" --exclude=PackageKit-gstreamer-plugin --allowerasing && sudo dnf groupupdate sound-and-video

## First install VMAF

git clone https://github.com/Netflix/vmaf.git
cd vmaf
make
sudo make install

## Now install x265

git clone https://bitbucket.org/multicoreware/x265_git
cd x265_git/build/linux
./make-Makefiles.bash
make
sudo make install

cd ~
git clone https://git.ffmpeg.org/ffmpeg.git ffmpeg
cd ffmpeg
./configure --enable-gpl --enable-libx265
make
sudo make install
