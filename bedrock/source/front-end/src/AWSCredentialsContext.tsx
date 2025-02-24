// src/context/AwsCredentialsContext.js
import React, { createContext, useContext, useState, useEffect } from "react";
import { fetchAuthSession } from "@aws-amplify/auth";
import type { AwsCredentials } from './types';
import { $appConfig } from "./stores/appConfig";
import { useStore } from "@nanostores/react";

const AwsCredentialsContext = createContext<AwsCredentials | null>(null);

export const useAwsCredentials = () => {
  return useContext(AwsCredentialsContext);
};

interface AwsCredentialsProviderProps {
  children: React.ReactNode;
}

export const AwsCredentialsProvider: React.FC<AwsCredentialsProviderProps> = ({ children }) => {
  const [awsCredentials, setAwsCredentials] = useState<AwsCredentials | null>(null);
  const appConfig = useStore($appConfig)

  useEffect(() => {
    const fetchAwsCredentials = async () => {
      try {
        const userSession = await fetchAuthSession();
        const email: string = userSession.tokens?.idToken?.payload.email as string ?? '';
        const username: string = userSession.tokens?.idToken?.payload.name as string ?? '';

        // Check if credentials are available before setting state
        if (userSession?.credentials) {
            const awsCredentials = userSession.credentials
            setAwsCredentials({
                region: appConfig?.region || "us-east-1",
                username: email,
                email: email,
                ...awsCredentials
            });
        } else {
          console.warn("No credentials found in session");
        }
      } catch (error) {
        console.error("Failed to get AWS credentials:", error);
      }
    };

    fetchAwsCredentials();
  }, []);

  return (
    <AwsCredentialsContext.Provider value={awsCredentials}>
      {children}
    </AwsCredentialsContext.Provider>
  );
};
