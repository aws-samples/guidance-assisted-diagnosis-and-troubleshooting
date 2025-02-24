import { ChatApiClient } from "./chat-api-client";

export class ApiClient {
  private _chatClient: ChatApiClient | undefined;
  private apiURL: string;

  constructor(apiURL: string) {
    this.apiURL = apiURL;
  }


  public get chatClient() {
    if (!this._chatClient) {
      this._chatClient = new ChatApiClient(this.apiURL);
    }

    return this._chatClient;
  }
}