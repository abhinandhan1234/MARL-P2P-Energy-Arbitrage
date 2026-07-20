import { motion } from "framer-motion"; import GridTopology from "../components/SmartGrid/GridTopology";
export default function SmartGrid(){return <motion.div initial={{opacity:0,y:8}} animate={{opacity:1,y:0}} className="page"><div className="page-title"><div><p>PHYSICAL SAFETY LAYER</p><h1>Smart grid topology</h1></div></div><GridTopology/></motion.div>}
