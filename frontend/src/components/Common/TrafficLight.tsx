interface Props {
  status: 'green' | 'yellow' | 'red' | 'grey'
  size?: number
}

const colors = {
  green: '#27ae60',
  yellow: '#f39c12',
  red: '#e74c3c',
  grey: '#bdc3c7',
}

const labels = {
  green: 'All documents valid',
  yellow: 'Pending verification',
  red: 'Missing / expired documents',
  grey: 'Not checked',
}

export default function TrafficLight({ status, size = 14 }: Props) {
  return (
    <span
      title={labels[status]}
      style={{
        display: 'inline-block',
        width: size,
        height: size,
        borderRadius: '50%',
        backgroundColor: colors[status],
        flexShrink: 0,
      }}
    />
  )
}
