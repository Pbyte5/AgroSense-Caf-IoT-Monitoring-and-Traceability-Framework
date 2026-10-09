import clsx from 'clsx';
import Heading from '@theme/Heading';
import styles from './styles.module.css';

const FeatureList = [
  {
    title: 'Farm and crop monitoring',
    description: (
      <>
        Bring farm, plot, and sensor data together to understand field
        conditions across coffee-growing regions.
      </>
    ),
  },
  {
    title: 'Agronomic insights',
    description: (
      <>
        Use weather and IoT observations to identify crop risks and support
        timely decisions in the field.
      </>
    ),
  },
  {
    title: 'Coffee traceability',
    description: (
      <>
        Preserve the origin of export lots with records that connect coffee
        back to its contributing farms.
      </>
    ),
  },
];

function Feature({title, description}) {
  return (
    <div className={clsx('col col--4')}>
      <div className="text--center padding-horiz--md">
        <Heading as="h3">{title}</Heading>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures() {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
