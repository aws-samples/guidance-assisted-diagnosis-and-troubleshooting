export const getEnvCredentials = () => {
    if (
      process.env.REACT_APP_AWS_ACCESS_KEY_ID == null ||
      process.env.REACT_APP_AWS_SECRET_ACCESS_KEY == null
    ) {
      throw new Error(
        'Missing credentials: must provide the following env variables: VITE_AWS_ACCESS_KEY_ID, VITE_AWS_SECRET_ACCESS_KEY within .env.local'
      );
    }
    return {
      // Provided by `.env.local` environment variable file
      accessKeyId: process.env.REACT_APP_AWS_ACCESS_KEY_ID,
      secretAccessKey: process.env.REACT_APP_AWS_SECRET_ACCESS_KEY,
      sessionToken: process.env.REACT_APP_AWS_SESSION_TOKEN,
    };
  };