import { Container, Grid, Header } from "@awsui/components-react";
import { useStore } from "@nanostores/react"
import { KPI } from "@iot-app-kit/react-components";
import { $appConfig } from '../../stores/appConfig'

function MachineKPIs(props: any){
    const appConfig = useStore($appConfig);

    const OEE_PROPERTY=appConfig?.roasterOEEProperty
    const PERFORMANCE_PROPERTY = appConfig?.roasterPerformanceProperty
    const QUALITY_PROPERTY = appConfig?.roasterQualityProperty
    const UTILIZATION_PROPERTY = appConfig?.roasterUtilizationProperty

    return(
        <Container 
            disableContentPaddings={true} 
            header={<Header variant="h2" description="The current KPIs of the machine"> {props.assetName} KPIs </Header>}
        >
            <Grid gridDefinition={[
                { colspan: { l: 3, m: 3, default: 3 } },
                { colspan: { l: 3, m: 3, default: 3 } },
                { colspan: { l: 3, m: 3, default: 3 } },
                { colspan: { l: 3, m: 3, default: 3 } },
            ]}>
                <KPI
                query={
                    props.query.timeSeriesData({
                    assets: [{ assetId: props.assetId, properties: [{ propertyId: OEE_PROPERTY, refId: 'oee-property' }] }]
                    })
                }
                thresholds={[
                    { value: 85, color: 'green', comparisonOperator: 'GTE', label: { text: 'Optimal', show: true }, severity: 1 },
                    { value: 70, color: 'orange', comparisonOperator: 'LT', label: { text: 'Needs Attention', show: true }, severity: 2 },
                    { value: 50, color: 'red', comparisonOperator: 'LT', label: { text: 'Critical', show: true }, severity: 3 }
                ]}
                settings={{
                    showTimestamp: true,
                    showUnit: true,
                    showName: true,
                    fontSize: 30,
                    secondaryFontSize: 15,
                }}
                styles={{
                    'oee-property': { name: 'OEE', unit: '%' },
                }}
                significantDigits={0} 
                />
                <KPI
                    query={
                    props.query.timeSeriesData({
                        assets: [{ assetId: props.assetId, properties: [{ propertyId: PERFORMANCE_PROPERTY, refId: 'performance-property' }] }]
                    })
                    }
                    thresholds={[
                    { value: 90, color: 'green', comparisonOperator: 'GTE', label: { text: 'High Performance', show: true}, severity: 1 },
                    { value: 70, color: 'orange', comparisonOperator: 'LT', label: {text: 'Moderate Performance', show: true}, severity: 2 },
                    { value: 50, color: 'red', comparisonOperator: 'LT', label: {text: 'Low Performance', show: true}, severity: 3 }
                    ]}
                    settings={{
                    showTimestamp: true,
                    showUnit: true,
                    showName: true,
                    fontSize: 30,
                    secondaryFontSize: 15,
                    }}
                    styles={{
                    'performance-property': { name: 'Performance', unit: '%' },
                    }}
                    significantDigits={0} 
                />
                <KPI
                    query={
                        props.query.timeSeriesData({
                        assets: [{ assetId: props.assetId, properties: [{ propertyId: QUALITY_PROPERTY, refId: 'quality-property' }] }]
                        })
                    }
                    thresholds={[
                        { value: 85, color: 'green', comparisonOperator: 'GTE', label: { text: 'Optimal', show: true }, severity: 1 },
                        { value: 70, color: 'orange', comparisonOperator: 'LT', label: { text: 'Needs Attention', show: true }, severity: 2 },
                        { value: 50, color: 'red', comparisonOperator: 'LT', label: { text: 'Critical', show: true }, severity: 3 }
                    ]}
                    settings={{
                        showTimestamp: true,
                        showUnit: true,
                        showName: true,
                        fontSize: 30,
                        secondaryFontSize: 15,
                    }}
                    styles={{
                        'quality-property': { name: 'Quality', unit: '%' },
                    }}
                    significantDigits={0} 
                />
                <KPI
                    query={
                    props.query.timeSeriesData({
                        assets: [{ assetId: props.assetId, properties: [{ propertyId: UTILIZATION_PROPERTY, refId: 'utilization-property' }] }]
                    })
                    }
                    thresholds={[
                    { value: 90, color: 'green', comparisonOperator: 'GTE', label: { text: 'High Performance', show: true}, severity: 1 },
                    { value: 70, color: 'orange', comparisonOperator: 'LT', label: {text: 'Moderate Performance', show: true}, severity: 2 },
                    { value: 50, color: 'red', comparisonOperator: 'LT', label: {text: 'Low Performance', show: true}, severity: 3 }
                    ]}
                    settings={{
                    showTimestamp: true,
                    showUnit: true,
                    showName: true,
                    fontSize: 30,
                    secondaryFontSize: 15,
                    }}
                    styles={{
                    'utilization-property': { name: 'Utilization', unit: '%' },
                    }}
                    significantDigits={0} 
                />
            </Grid>
        </Container>
    )
}


export default MachineKPIs