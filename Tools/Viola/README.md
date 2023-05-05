# Viola
Viola is a tool for detecting vulnerable image hosting modules in the wild. It mainly consists of the following three parts.



## Context Collect

In **Section 5.1** "Semantic Analyzer", this code is used to collect the context around the upload points. After locating the upload points with the signature of `<input type="file">`, it adopts the DFS algorithm to traverse the HTML elements around the upload point and continuously expand the range until the difference in text density exceeds the threshold.



## Context Analyze

In **Section 5.1** "Semantic Analyzer", this code is used to analyze the context collected by `context_collect.js` to check semantic inconsistency of the upload points. Firstly, it unifies all text into English by using Baidu Translation API. Then, with the Google pre-trained BERT model, it generates feature vectors of the context.

By comparing the Euclidean distance between the candidate web service and the semantics of 50 manually annotated IHMs, if the minimum distance is larger than the threshold, we take it semantics of such web service is inconsistent with IHMs.



## Lifecycle Assessor

In **Section 5.2** "Upload Lifecycle Assessor", this code provides an automatic image upload function, which can imitate user interaction with the IHM and monitor the corresponding network traffic, telling whether there is a vulnerability and where it is. 

This assessor is built with the Puppeteer library in Node.js. To trigger the upload process, the assessor performs the following three steps - 1) Selecting image from local path, 2) Filling the required fields, 3) submit the forms. Based on the traffic analysis, the assessor can detect vulnerabilities on four stages by detecting the leaked url of uploaded beacon image.

+ Between step 1 and step 3
  + Leakage in response content of POST/PUT method - **Presubmit Stage**
  + Leakage in request url - **Preview Stage**
+ After step 3
  + Leakage in response content of POST/PUT method - **Submit Stage**
  + Leakage in request url - **Callback Stage**

During the process of monitoring network traffic, it is important to exclude the noise by assessing image similarity. Firstly, we compare the image hash consistency. If failed, we leverage hamming distance between the perceptual hashes of the downloaded image and the beacon. If the difference is below the threshold, we consider the returned image to be identical to the beacon image. These identical images could lead to vulnerabilities.

