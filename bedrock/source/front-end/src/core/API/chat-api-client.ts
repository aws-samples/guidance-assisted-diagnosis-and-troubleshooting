import { ApiClientBase } from "./api-client-base";

export class ChatApiClient extends ApiClientBase {
  private apiURL: string;

  constructor(apiURL: string) {
    super();
    this.apiURL = apiURL;
  }

  async chat(message: string): Promise<any> {
    try {
      const headers = await this.getHeaders();
      const session_id = await this.getSessionID()

      const response = await fetch(this.apiURL, {
        method: "POST",
        headers: {
          ...headers,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: message,
          session_id: session_id,
        }),
      });


      if (!response.ok) {
        throw new Error(`Network response was not ok: ${response.statusText}`);
      }

      const data = await response.json();

      return data;

    } catch (error) {
      console.error("Error in chat function:", error); 
      throw error;
    }
  }
}
