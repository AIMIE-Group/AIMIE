# AIMIE

The repository for "Understanding and Detecting Abused Image Hosting Modules as Malicious Services".

Refer to [link](https://github.com/AIMIE-Group/AIMIE/blob/main/ccs23-AIMIE.pdf) for the online version of our paper's artifacts.

## Structure

### Datasets

- We presents the first measurement study of Abused Image Hosting Modules as Malicious (AIMIE) Services. The full list of 89 AIMIE services we collect is in `Datasets/AIMIE_List.txt`.

- In **Section 3.2.2** "Upload/gateway API triage", we collect the image hosting platforms through search engines and reach a list with 98 hosting services which is in `Datasets/Public_Image_Hosting_Platform_List.txt`.

### Tools

- In **Section 3.2.2** "Abused endpoint recognition", we extract upload endpoints from source codes written in multiple programming languages. The source code for this tool is present in `Tools/Multiple_Language_Interpreter/`.
- In **Section 5** "VULNERABLE IHMS IN THE WILD", we build Viola to detect vulnerable image hosting module in the wild. The relevant codes for Viola can be found in `Tools/Viola/`.
