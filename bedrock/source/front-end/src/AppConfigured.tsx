import { useEffect, useState } from "react";
import { AwsCredentialsProvider } from "./AWSCredentialsContext";
import {
  Alert,
  Authenticator,
  Heading,
  useTheme,
} from "@aws-amplify/ui-react";
import { StatusIndicator } from "@cloudscape-design/components";
import { Amplify, ResourcesConfig, } from "aws-amplify";
import { $appConfig } from './stores/appConfig';
import type { AppConfig } from "./types";
import App from "./App";
import "@aws-amplify/ui-react/styles.css";



export default function AppConfigured() {
  const { tokens } = useTheme();
  const [config, setConfig] = useState<ResourcesConfig | null>(null);
  const [error, setError] = useState<boolean | null>(null);
  

  useEffect(() => {
    (async () => {
      try {
        const appConfig: AppConfig = {
          region: process.env.REACT_APP_AWS_REGION || "",
          cognitoClientId: process.env.REACT_APP_COGNITO_CLIENT_ID || "",
          cognitoIdentityPoolId: process.env.REACT_APP_COGNITO_IDENTITY_POOL_ID || "",
          cognitoUserPoolId: process.env.REACT_APP_COGNITO_USER_POOL_ID || "",
          restApiEndpoint: process.env.REACT_APP_REST_API_ENDPOINT|| "",
          roasterId: process.env.REACT_APP_ROASTER_ID|| "",
          roasterHoldTimeProperty: process.env.REACT_APP_HOLD_TIME_PROPERTY|| "",
          roasterTemperatureProperty: process.env.REACT_APP_TEMPERATURE_PROPERTY|| "",
          roasterScrapProperty: process.env.REACT_APP_SCRAP_PROPERTY|| "",
          roasterOEEProperty: process.env.REACT_APP_OEE_PROPERTY|| "",
          roasterPerformanceProperty: process.env.REACT_APP_PERFORMANCE_PROPERTY|| "",
          roasterQualityProperty: process.env.REACT_APP_QUALITY_PROPERTY|| "",
          roasterUtilizationProperty: process.env.REACT_APP_UTILIZATION_PROPERTY|| "",
        };

        const missingKeys = Object.entries(appConfig)
          .filter(([key, value]) => !value)
          .map(([key]) => key);

        if (missingKeys.length > 0) {
          console.error(`Missing required configuration: ${missingKeys.join(", ")}`);
          setError(true);
          return;
        }

        $appConfig.set(appConfig)

        const amplifyConfig: ResourcesConfig = {
            Auth: {
                Cognito: {
                    userPoolClientId: appConfig.cognitoClientId ,
                    userPoolId: appConfig.cognitoUserPoolId,
                    identityPoolId: appConfig.cognitoIdentityPoolId
                }
            },
            API: {
              REST: {
                AssistedDiagnosesRestApi: {
                  endpoint: appConfig.restApiEndpoint
                }
              }
            }
        };

        Amplify.configure(amplifyConfig);

        setConfig(amplifyConfig);
      } catch (e) {
        console.error(e);
        setError(true);
      }
    })();
  }, []);


  if (!config) {
    if (error) {
      return (
        <div
          style={{
            height: "100%",
            width: "100%",
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          <Alert heading="Configuration error" variation="error">
            Error loading configuration from env variables"
          </Alert>
        </div>
      );
    }

    return (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <StatusIndicator type="loading">Loading</StatusIndicator>
      </div>
    );
  }

  
  return (
      <Authenticator
        hideSignUp={true}
        components={{
          SignIn: {
            Header: () => {
              return (
                <Heading
                  padding={`${tokens.space.xl} 0 0 ${tokens.space.xl}`}
                  level={3}
                >
                  Assisted Diagnoses and Troubleshooting
                </Heading>
              );
            },
          },
        }}
      >
        <AwsCredentialsProvider>
            <App />
        </AwsCredentialsProvider>
      </Authenticator>
  );
}