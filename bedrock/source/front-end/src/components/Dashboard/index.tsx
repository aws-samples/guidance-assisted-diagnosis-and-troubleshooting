import { useState, useEffect, useRef } from 'react';
import { AppLayout, BreadcrumbGroup, Container, Grid, Header, TopNavigation } from "@awsui/components-react";
import { ResourceExplorer, Chart, WebglContext, KPI } from "@iot-app-kit/react-components";
import MachineKPIs from "../MachineKPIs"
import ChatView from "../Chat-UI/Chat-view"
import { ReactComponent as ChatIcon } from './chat.svg';
import { useStore } from "@nanostores/react"
import { $client} from '../../stores/iotsitewise';
import { $eventsClient } from '../../stores/iotevents';
import { $user } from '../../stores/users'
import { $appConfig } from '../../stores/appConfig'
import { initialize } from "@iot-app-kit/source-iotsitewise";
import {signOut}  from '@aws-amplify/auth';


function Breadcrumbs() {
    const breadcrumbItems = [
        {
            text: 'Brewery',
            href: '#'
        },
        {
            text: 'Roaster Dashboard',
            href: '#'
        }
    ];

    return <BreadcrumbGroup items={breadcrumbItems} expandAriaLabel="Show path" ariaLabel="Breadcrumbs" />;
}


function PageHeader() {
    return <Header variant="h1">Machine Dashboard</Header>;
}


function SitewiseResourceExplorer(props: any) {
    const columnDefinitions = [{
        sortingField: 'name',
        id: 'name',
        header: 'Asset Name',
        cell: ({ name }: any) => name,
    }];
  
    return (
        <Container 
            disableContentPaddings={true}
            header={ <Header variant="h2" description="List of SiteWise assets"> Bottling Line Machines </Header> }
        >
            <ResourceExplorer
              query={props.query.assetTree.fromRoot()}
              onSelectionChange={(event) => {
                  console.log("changes asset", event);
                  props.setAssetId((event?.detail?.selectedItems?.[0] as any)?.id);
                  props.setAssetName((event?.detail?.selectedItems?.[0] as any)?.name);
              }}
              columnDefinitions={columnDefinitions}
          />
        </Container>
    );
  }
  
  


function Content(props: any) {
    const appConfig = useStore($appConfig);
    const DEFAULT_MACHINE_ASSET_ID = appConfig?.roasterId;
    const [ assetId, setAssetId ] = useState(DEFAULT_MACHINE_ASSET_ID);
    const [ assetName, setAssetName ] = useState('Roaster');
    const [isMounted, setIsMounted] = useState(false);


    const HOLD_TIME_PROPERTY = appConfig?.roasterHoldTimeProperty
    const TEMPERATURE_PROPERTY = appConfig?.roasterTemperatureProperty
    const SCRAP_PROPERTY = appConfig?.roasterScrapProperty


    // const chartWidth = props.isChatOpen ? window.screen.width / 2.5 : (window.screen.width / 1.85)
    const containerRef = useRef<HTMLDivElement | null>(null);
    const smallChartRef = useRef<HTMLDivElement | null>(null);
    const [chartWidth, setChartWidth] = useState<number | null>(null);
    const [smallChartWidth, setsmallChartWidth] = useState<number | null>(null);


    useEffect(() => {
        const updateChartWidth = () => {
            if (containerRef.current) {
                setChartWidth(containerRef.current.offsetWidth);
            }
            if(smallChartRef.current){
              setsmallChartWidth(smallChartRef.current.offsetWidth)
            }
        };

        if (!isMounted) {
            setIsMounted(true);
        }

        window.addEventListener('resize', updateChartWidth);

        // Cleanup the event listener on component unmount
        return () => {
            window.removeEventListener('resize', updateChartWidth);
        };
    }, [isMounted]);

    useEffect(() => {
      // Trigger a resize event once to capture initial width after mounting
        if (isMounted && chartWidth === null) {
            setTimeout(() => window.dispatchEvent(new Event('resize')), 0);
        }
    }, [isMounted, chartWidth]);

  
    return(
        <Grid gridDefinition={[
          { colspan: { l: 3, m: 3, default: 12 } },
          { colspan: { l: 9, m: 9, default: 12 } },
      ]}>
          <SitewiseResourceExplorer query={props.query} setAssetId={setAssetId} setAssetName={setAssetName}/>
          <Grid gridDefinition={[
                    { colspan: { l: 12, m: 12, default: 12 } },
                    { colspan: { l: 3, m: 3, default: 3 } },
                    { colspan: { l: 9, m: 9, default: 9 } },
                    { colspan: { l: 6, m: 6, default: 6 } },
                    { colspan: { l: 6, m: 6, default: 6 } },
          ]}>
            <MachineKPIs query={props.query} assetId={assetId} assetName={assetName}/>
            <Container  disableContentPaddings={true} 
                  header={<Header variant="h2" description="Scrap of the machine"> {assetName} Scrap </Header>}>
              <div style={{ height: "250px" }}>
                <KPI
                  aggregationType="avg"
                  query={
                    props.query.timeSeriesData({
                      assets: [{
                        assetId: assetId,
                        properties: [
                          { propertyId: SCRAP_PROPERTY, refId: 'scrap-property' },
                        ]
                      }]
                    })
                  }
                  significantDigits={0}
                />
              </div>
            </Container>
            <Container  disableContentPaddings={true} 
                  header={<Header variant="h2" description="The current temperature of the machine"> {assetName} Temperature </Header>}>
              <div ref={containerRef} style={{ height: "250px" }}>
                {chartWidth && chartWidth > 0 && (
                  <Chart
                    aggregationType="avg"
                    size={{
                      width: props.isChatOpen ? chartWidth - 175: chartWidth , 
                      height: 230}}
                    legend={{visible: false}}
                    significantDigits={2}
                    queries={[
                      props.query.timeSeriesData({
                        assets: [{
                          assetId: assetId,
                          properties: [
                            { propertyId: TEMPERATURE_PROPERTY, refId: 'temperature-property' },
                          ]
                        }]
                      })
                    ]}
                  />
                )}
              </div>
            </Container>
            <Container  disableContentPaddings={true} 
                  header={<Header variant="h2" description="The current hold time of the machine"> {assetName} HoldTime </Header>}>
              <div ref={smallChartRef} style={{ height: "250px" }}>
                {smallChartWidth && smallChartWidth > 0 && (
                  <Chart
                    aggregationType="avg"
                    size={{width: props.isChatOpen ? smallChartWidth - 120: smallChartWidth, height: 230}}
                    legend={{visible: false}}
                    queries={[
                      props.query.timeSeriesData({
                        assets: [{
                          assetId: assetId,
                          properties: [
                            { propertyId: HOLD_TIME_PROPERTY, refId: 'temperature-property' },
                          ]
                        }]
                      })
                    ]}
                  />
                )}
              </div>
            </Container>
            <Container  disableContentPaddings={true} 
                  header={<Header variant="h2" description="The current status of the machine"> {assetName} Status </Header>}>
              <div style={{ height: "250px" }}>
                {smallChartWidth && smallChartWidth > 0 && (
                  <Chart 
                    axis={{
                        yMin: 0,
                        yMax: 1
                      }
                    }
                    size={{width: props.isChatOpen ? smallChartWidth - 120: smallChartWidth, height: 230}}
                    legend={{visible: false}}
                    queries={[
                      props.query.timeSeriesData({
                        assets: [{
                          assetId: assetId,
                          properties: [
                            { propertyId: '9df74a66-97f6-4e2f-8761-4af4b2a788fe', refId: 'runtime-property' },
                          ]
                        }]
                      })
                    ]}
                    thresholds={[
                      { value: 1, id: `runtime-xyz`, color: 'green', comparisonOperator: 'EQ',  dataStreamIds:['runtime-property']},
                      { value: 0, id: `runtime-xyz`, color: 'red', comparisonOperator: 'EQ',  dataStreamIds:['runtime-property']},
                    ]}
                  />
                )}  
              </div>
            </Container>
          </Grid>
      </Grid>
    )
  }


export function Dashboard() {
    const client = useStore($client);
    const user = useStore($user);
    const eventsClient = useStore($eventsClient);
    const [activeDrawerId, setActiveDrawerId] = useState<string | null>(null);

    const handleDrawerChange = (detail: { activeDrawerId: string | null }) => {
        setActiveDrawerId(detail.activeDrawerId);
    };
    const handleUtilityClick = async (e: CustomEvent) => {
        console.log('logging out', e)
        if (e.detail.id === "signout") {
          console.log('Signing out...');

          try {
              await signOut({
                global: true
              });
              
              console.log('Successfully signed out');
              
              window.location.href = '/';
          } catch (error) {
              console.error('Error signing out:', error);
          }
        }
    };

    if(!client || !eventsClient){
        return (
            <div>
                Clients are null
            </div>
        )
    }


    const {query} = initialize({ iotSiteWiseClient: client, iotEventsClient: eventsClient });


    return (
        <>
            <TopNavigation
                className={activeDrawerId ? 'DrawerOpened' : 'DrawerClosed'}
                identity={{
                    href: "#",
                    title: "Assisted Diagnosis and Troubleshooting Demo",
                }}
                i18nStrings={{ overflowMenuTriggerText: "More", overflowMenuTitleText: "More" }}
                utilities={[
                    {
                        type: "menu-dropdown",
                        text: user?.email,
                        description: user?.email,
                        iconName: "user-profile",
                        onItemClick: handleUtilityClick,
                        items: [
                            { id: "signout", text: "Sign out" }
                        ]
                    }
                ]}
            />
            <AppLayout
                breadcrumbs={<Breadcrumbs />}
                contentHeader={<PageHeader />}
                content={<Content query={query} isChatOpen={activeDrawerId ? true : false}/>}
                navigationHide={true}
                toolsHide={true}
                activeDrawerId={activeDrawerId}
                onDrawerChange={({ detail }) => handleDrawerChange(detail)}
                drawers={[
                    {
                        id: 'chat-assistant',
                        content: <ChatView />,
                        trigger: {
                            iconSvg: <ChatIcon />,
                        },
                        ariaLabels: {
                            drawerName: 'Chat Assistant',
                            closeButton: 'Close Chat Assistant',
                            triggerButton: 'Open Chat Assistant',
                            resizeHandle: 'Resize Chat Assistant',
                        },
                        badge: true,
                        resizable: true,
                        defaultSize: 300,
                    },
                ]}
                ariaLabels={{
                    navigation: "Navigation drawer",
                    navigationClose: "Close navigation drawer",
                    navigationToggle: "Open navigation drawer",
                    tools: "Tools drawer",
                    toolsClose: "Close tools drawer",
                    toolsToggle: "Open tools drawer",
                    drawers: "Drawers",
                    drawersOverflow: "Overflow drawers",
                    drawersOverflowWithBadge: "Overflow drawers (Unread notifications)"
                }}

            />
            {/* --- BEGIN: `WebglContext` implementation*/}
            <WebglContext />
            {/* --- END: `WebglContext` implementation*/}
        </>
    );
}

export default Dashboard