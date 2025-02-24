import { sha256 } from "js-sha256";
import { fetchAuthSession } from "aws-amplify/auth";

export abstract class ApiClientBase {
  protected async getHeaders() {
    return {
      Authorization: `Bearer ${await this.getIdToken()}`,
    };
  }

  protected async getIdToken() {
    const session = await fetchAuthSession();

    return session.tokens?.idToken?.toString();
  }

  protected async getSessionID(): Promise<string> {
    const id_token = await this.getIdToken();
    if (id_token) {
      return sha256(id_token);
    } else {
      throw new Error("ID Token is undefined");
    }
  }
}