export default () => (
  <board
    title="Board Element Demo"
    width="40mm"
    height="30mm"
    borderRadius="2mm"
    layers={4}
    material="fr4"
    thickness="1.6mm"
    solderMaskColor="green"
  >
    <resistor name="R1" resistance="1k" footprint="0805" pcbX={-9} pcbY={4} schX={-2.38} schY={1} />
    <led name="LED1" color="green" footprint="0603" pcbX={0} pcbY={4} schX={1.76} schY={1} />
    <capacitor name="C1" capacitance="100nF" footprint="0805" pcbX={9} pcbY={4} schX={3} schY={1} schOrientation="vertical" />
    <chip name="U1" footprint="soic8" pcbX={0} pcbY={-5} schX={-0.38} schY={1.49} />
    <trace from=".R1 > .pin2" to=".LED1 > .anode" />
    <trace from=".LED1 > .cathode" to=".U1 > .pin1" />
    <trace from=".C1 > .pin1" to=".U1 > .pin8" />
  </board>
)
