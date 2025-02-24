## Demo Script
In this scenario, you'll play the role of Martha Maintenance, a technician in the reliability team. Martha has received an alert about an issue with the roaster and needs to diagnose the problem, consult the Standard Operating Procedures (SOPs), and potentially create a work order for repairs.

1. Martha wants to start investigating the issue. Since we don't know the exact name of the asset in our data store, let's begin by listing the assets:

    ```
    Hey there! I'm just starting my shift and need to get my bearings. Could you give me a quick rundown of all the assets we've got in the system? A simple bullet point list would be perfect.
    ```

    This will give you an overview of all the assets in the system.

    ![ui-1](/bedrock/assets/query1.png)


2. Now that we have a list of assets, let's check the status of the roaster:

    ```
    Thanks for that list. I heard there might be an issue with the roaster. Can you tell me if it's currently up and running?
    ```

    This will tell us if the roaster is operational or if it has already shut down due to the issue.

    ![ui-2](/bedrock/assets/query2.png)

    Although the machine appears to be operating without reported issues, the grains are not being roasted evenly. Martha needs to consult the SOP for possible causes of the problem. This is information that will come from knowledgebase instead of telemetry data

3. To consult the SOP for possible causes of uneven roasting ask:
    ```
    It's good to know that the machine is running, but roasting seems to be uneven. What are the possible causes of uneven roasting?
    ```

    This will provide information from the Standard Operating Procedures about potential issues that could cause uneven roasting. Note that sources from the document(s) used to answer the question are provided

    ![ui-3](/bedrock/assets/query3.png)

4. Now that we know what to check, we can go back to our telemetry data to verify that the asset is operating within the allowed range.

    Let's check the current temperature of the roaster:
    ```
    Alright, I've got a few ideas of what might be wrong. Can you give me a quick temperature reading on Roaster100? I want to make sure it's not running too hot or too cold.
    ```
    This will help us determine if the temperature is within the normal operating range.

    ![ui-4](/bedrock/assets/query4.png)

5. Let's say that the temperature value appears to be abnormal, so we need to analyze this further. We are going to go back to our internal documentation to gather more information, Martha now can ask how to inspect the heating elements:
    ```
    The temperature's not looking right. I think I need to take a look at the heating elements. How do I inspect the heating elements for signs of wear or malfunction?
    ```
    This will provide Martha with the necessary steps to check the heating elements.

    ![ui-5](/bedrock/assets/query5.png)

6. Now that we have all of this information, it's time to create a work order. Create a work order with the following prompt. Notice that we do not have to mention the asset, the operating conditions, or the assets that we want to check — all of this information will be extracted from the chat history by the AI assistant.

    ```
    Based on our inspection and the SOP guidelines, let's create a work order to address the uneven roasting issue
    ```
    ![ui-6](/bedrock/assets/query6.png)

    This will submit workorder to workorder API