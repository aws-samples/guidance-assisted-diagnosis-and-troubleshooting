
export type AwsCredentials = {
  accessKeyId: string;
  expiration?: Date;
  region: string;
  secretAccessKey: string;
  sessionToken?: string;
  username: string;
  email: string
};


export type User = {
  email: string;
  username: string
  readonly awsCredentials: Readonly<AwsCredentials>;
  // readonly id: string;
};

export type AppConfig = {
  region: string;
  cognitoClientId: string;
  cognitoIdentityPoolId: string;
  cognitoUserPoolId: string;
  restApiEndpoint: string;
  roasterId: string,
  roasterHoldTimeProperty: string,
  roasterTemperatureProperty: string,
  roasterScrapProperty: string,
  roasterOEEProperty: string,
  roasterPerformanceProperty: string,
  roasterQualityProperty: string,
  roasterUtilizationProperty: string
}
