import React, { useState } from "react";
import { useStore } from "@nanostores/react"
import { ChatUI } from "./chat-ui";
import { ChatMessage, ChatMessageType } from "./types";
import { Badge, SpaceBetween } from "@cloudscape-design/components";
import { ApiClient } from "../../core/API/api-client";
import { $appConfig } from '../../stores/appConfig';


export default function ChatView() {
  const [running, setRunning] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const appConfig = useStore($appConfig)


  const renderExpandableContent = (message: ChatMessage) => {
    return (
      message.type === ChatMessageType.AI ?
        <React.Fragment>
          <SpaceBetween size="xs" direction="horizontal">
            <Badge color="blue">
              latency: {message.metadata?.latencyMs}ms
            </Badge>
          </SpaceBetween>
        </React.Fragment> :
        undefined
    )
  }
  const sendMessage = async (message: string) => {
    setRunning(true);
    setMessages((prevMessages) => [
      ...prevMessages,
      { type: ChatMessageType.Human, content: message },
      { type: ChatMessageType.AI, content: "" }
    ])

    const apiURL = appConfig?.restApiEndpoint || ""
    const apiClient = new ApiClient(apiURL); 

    const startTime = performance.now();
    const result = await apiClient.chatClient.chat(message);
    const endTime = performance.now();


    const elapsedTime = endTime - startTime;

    setMessages((prevMessages) => [
      ...prevMessages.slice(0, prevMessages.length - 1), // Copy all but the last item
      {
        type: ChatMessageType.AI,
        content: result.response.answer + " \n" + result.response.source,
        metadata: { latencyMs: elapsedTime }
      },
    ]);
    setRunning(false);
  };

  const onSendFeedback = (feedback: any, message: ChatMessage) => {
    console.log(feedback, message);
  }

  return (
    <ChatUI
      onSendMessage={sendMessage}
      messages={messages}
      running={running}
      onSendFeedback={onSendFeedback}
      renderExpandableContent={renderExpandableContent}
    />
  );
}