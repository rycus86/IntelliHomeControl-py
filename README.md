IntelliHomeControl / Python
===========================

This Eclipse project is the server part of the IntelliHomeControl home automation system.
The application is written in Python to run on a Raspberry Pi.

The system controls devices with RF communication and displays their states on Android clients.

Components
----------

 - Database module for SQLite
 - Abstract device classes
 - RF communication manager for nRF24L01+
 - TCP/UDP based handlers to communicate with Android clients

There are sources for TI's Energia IDE that contain:

 - Modified Enrf24 library (original: https://github.com/spirilis/Enrf24)
 - ihControl library to implement RF communication protocol with the server
 - Device implementation for TI Stellaris LM4F120
 - Device implementation for TI Tiva TM4C123G

Android client
--------------

The source of the Android client is available at https://github.com/rycus86/IntelliHomeControl-android
